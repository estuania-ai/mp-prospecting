"""
Blueprint: /api/whatsapp
Gestión de Evolution API: estado, QR, envío manual, historial, webhook entrante.
"""

from flask import Blueprint, jsonify, request
from datetime import datetime
import logging

from database import get_db
from whatsapp import evolution_client as ev

logger = logging.getLogger(__name__)
bp = Blueprint('whatsapp', __name__, url_prefix='/api/whatsapp')


# ── ESTADO Y CONEXIÓN ────────────────────────────────────────────

@bp.get('/status')
def wa_status():
    """Estado de la instancia Evolution API."""
    state = ev.get_connection_state()
    return jsonify(state)


@bp.get('/qr')
def wa_qr():
    """Obtiene el QR code en base64 para escanear."""
    result = ev.get_qr_code()
    return jsonify(result)


@bp.post('/connect')
def wa_connect():
    """Asegura que la instancia exista y retorna estado."""
    ev.ensure_instance_exists()
    state = ev.get_connection_state()
    return jsonify(state)


@bp.post('/disconnect')
def wa_disconnect():
    """Desconecta la sesión WhatsApp (el número queda libre)."""
    result = ev.logout_instance()
    return jsonify(result)


@bp.post('/restart')
def wa_restart():
    """Reinicia la instancia (útil si se cuelga)."""
    result = ev.restart_instance()
    return jsonify(result)


# ── ENVÍO MANUAL ─────────────────────────────────────────────────

@bp.post('/send')
def wa_send():
    """
    Envía un mensaje a un número.
    Body: { "phone": "56912345678", "message": "Hola!", "image_url": "..." (opcional) }
    """
    data = request.get_json() or {}
    phone = data.get('phone', '').strip()
    message = data.get('message', '').strip()
    image_url = data.get('image_url', '').strip() or None

    if not phone or not message:
        return jsonify({"ok": False, "error": "phone y message son requeridos"}), 400

    result = ev.send_message(phone, message, image_url)

    # Registrar en BD
    if result.get("ok"):
        _save_wa_message(phone=phone, message_text=message, status='sent',
                         wa_message_id=result.get("data", {}).get("key", {}).get("id"),
                         message_type='manual')

    return jsonify(result)


# ── HISTORIAL ────────────────────────────────────────────────────

@bp.get('/messages')
def wa_messages():
    """Lista mensajes WA enviados con paginación."""
    page     = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 50))
    phone    = request.args.get('phone', '').strip()
    offset   = (page - 1) * per_page

    conn = get_db()
    where = "WHERE phone LIKE ?" if phone else ""
    params_count = (f"%{phone}%",) if phone else ()
    params_data  = (f"%{phone}%", per_page, offset) if phone else (per_page, offset)

    total = conn.execute(
        f"SELECT COUNT(*) FROM wa_messages {where}", params_count
    ).fetchone()[0]

    rows = conn.execute(
        f"""SELECT id, phone, message_type, message_text, status,
                   sent_at, delivered_at, read_at, replied_at, reply_text,
                   rubro, comuna, wa_message_id
            FROM wa_messages {where}
            ORDER BY sent_at DESC
            LIMIT ? OFFSET ?""",
        params_data
    ).fetchall()
    conn.close()

    return jsonify({
        "total": total,
        "page": page,
        "per_page": per_page,
        "messages": [dict(r) for r in rows]
    })


@bp.get('/stats')
def wa_stats():
    """KPIs de WhatsApp: enviados, entregados, leídos, respondidos."""
    conn = get_db()
    stats = conn.execute("""
        SELECT
            COUNT(*)                                          AS total_sent,
            SUM(CASE WHEN delivered_at IS NOT NULL THEN 1 ELSE 0 END) AS delivered,
            SUM(CASE WHEN read_at      IS NOT NULL THEN 1 ELSE 0 END) AS read,
            SUM(CASE WHEN replied_at   IS NOT NULL THEN 1 ELSE 0 END) AS replied,
            SUM(CASE WHEN status = 'failed'        THEN 1 ELSE 0 END) AS failed
        FROM wa_messages
        WHERE date(sent_at) >= date('now', '-30 days')
    """).fetchone()

    daily = conn.execute("""
        SELECT date(sent_at) AS day, COUNT(*) AS cnt
        FROM wa_messages
        WHERE date(sent_at) >= date('now', '-7 days')
        GROUP BY day ORDER BY day
    """).fetchall()

    conn.close()
    return jsonify({
        "last_30_days": dict(stats),
        "daily_last_7": [dict(r) for r in daily]
    })


@bp.get('/conversations')
def wa_conversations():
    """Lista de conversaciones agrupadas por número."""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            m.phone,
            MAX(m.sent_at)    AS last_sent,
            COUNT(m.id)       AS messages_sent,
            SUM(CASE WHEN m.replied_at IS NOT NULL THEN 1 ELSE 0 END) AS replied,
            i.last_received,
            i.last_text
        FROM wa_messages m
        LEFT JOIN (
            SELECT phone,
                   MAX(received_at) AS last_received,
                   message_text     AS last_text
            FROM wa_incoming
            GROUP BY phone
        ) i ON i.phone = m.phone
        GROUP BY m.phone
        ORDER BY last_sent DESC
        LIMIT 100
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


# ── WEBHOOK (Evolution API → Flask) ─────────────────────────────

@bp.post('/webhook')
def wa_webhook():
    """
    Recibe eventos de Evolution API:
    - MESSAGES_UPSERT: mensaje entrante
    - MESSAGES_UPDATE: cambio de estado (delivered, read)
    - CONNECTION_UPDATE: cambio de estado de conexión
    """
    payload = request.get_json(silent=True) or {}
    event   = payload.get("event", "")

    try:
        if event == "MESSAGES_UPSERT":
            _handle_incoming(payload)
        elif event == "MESSAGES_UPDATE":
            _handle_status_update(payload)
        elif event == "CONNECTION_UPDATE":
            _handle_connection_update(payload)
    except Exception as e:
        logger.error(f"[Webhook] Error procesando evento {event}: {e}")

    return jsonify({"ok": True}), 200


# ── FOLLOW-UP MANUAL ─────────────────────────────────────────────

@bp.post('/followup/send')
def wa_followup_manual():
    """
    Dispara follow-up WhatsApp manualmente para contactos de email
    sin respuesta hace más de N días.
    """
    from jobs.wa_followup import run_wa_followup
    result = run_wa_followup()
    return jsonify(result)


@bp.post('/retry-failed')
def wa_retry_failed():
    """Elimina mensajes fallidos de números móviles (569) para que sean
    reintentados por el follow-up, y luego ejecuta el follow-up."""
    from jobs.wa_followup import run_wa_followup
    conn = get_db()
    # Eliminar registros fallidos de números móviles válidos (569XXXXXXXX)
    # Los teléfonos pueden tener espacios: "+56 9 1234 5678" → comparar sin espacios
    deleted = conn.execute("""
        DELETE FROM wa_messages
        WHERE status = 'failed'
          AND REPLACE(REPLACE(phone, ' ', ''), '+', '') LIKE '569%'
    """).rowcount
    conn.commit()
    conn.close()
    logger.info(f"[Retry] Eliminados {deleted} mensajes fallidos para reintento")
    # Ejecutar follow-up inmediatamente
    result = run_wa_followup()
    result['retried'] = deleted
    return jsonify(result)


# ── HELPERS INTERNOS ─────────────────────────────────────────────

def _save_wa_message(phone, message_text, status='sent', wa_message_id=None,
                     message_type='prospecting', rubro=None, comuna=None,
                     lead_id=None, et_contact_id=None, campaign_id=None):
    conn = get_db()
    conn.execute("""
        INSERT INTO wa_messages
            (phone, message_text, status, wa_message_id, message_type,
             rubro, comuna, lead_id, et_contact_id, campaign_id, sent_at, source)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'evolution')
    """, (phone, message_text, status, wa_message_id, message_type,
          rubro, comuna, lead_id, et_contact_id, campaign_id,
          datetime.now().strftime('%Y-%m-%d %H:%M:%S')))
    conn.commit()
    conn.close()


def _handle_incoming(payload):
    """Guarda mensaje entrante y marca replied en wa_messages."""
    data    = payload.get("data", {})
    key     = data.get("key", {})
    msg_id  = key.get("id", "")
    phone   = key.get("remoteJid", "").replace("@s.whatsapp.net", "")
    text    = (data.get("message", {}).get("conversation")
               or data.get("message", {}).get("extendedTextMessage", {}).get("text", "")
               or "")
    from_me = key.get("fromMe", False)

    if from_me or not phone:
        return

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()

    # Guardar entrante
    try:
        conn.execute("""
            INSERT OR IGNORE INTO wa_incoming (phone, message_id, message_text, received_at)
            VALUES (?, ?, ?, ?)
        """, (phone, msg_id, text, now))
    except Exception as e:
        logger.warning(f"[Webhook] wa_incoming insert: {e}")

    # Marcar replied en último mensaje enviado a ese número
    conn.execute("""
        UPDATE wa_messages
        SET replied_at = ?, reply_text = ?
        WHERE phone = ? AND replied_at IS NULL
        ORDER BY sent_at DESC LIMIT 1
    """, (now, text[:500], phone))

    # Marcar estado_interes en et_contacts si existe
    conn.execute("""
        UPDATE et_contacts
        SET estado_interes = 'respondio_wa'
        WHERE phone = ? AND estado_interes = 'pendiente'
    """, (phone,))

    conn.commit()
    conn.close()
    logger.info(f"[Webhook] Mensaje entrante de {phone}: {text[:80]}")


def _handle_status_update(payload):
    """Actualiza delivered_at / read_at en wa_messages."""
    updates = payload.get("data", [])
    if not isinstance(updates, list):
        updates = [updates]

    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()

    for upd in updates:
        key     = upd.get("key", {})
        msg_id  = key.get("id", "")
        status  = upd.get("update", {}).get("status", "")

        if not msg_id:
            continue

        if status == "DELIVERY_ACK":
            conn.execute(
                "UPDATE wa_messages SET delivered_at=? WHERE wa_message_id=?",
                (now, msg_id)
            )
        elif status == "READ":
            conn.execute(
                "UPDATE wa_messages SET read_at=?, delivered_at=COALESCE(delivered_at,?) WHERE wa_message_id=?",
                (now, now, msg_id)
            )

    conn.commit()
    conn.close()


def _handle_connection_update(payload):
    state = payload.get("data", {}).get("state", "unknown")
    logger.info(f"[Webhook] Conexión WA: {state}")
    # Guardar en config para que el dashboard lo muestre
    conn = get_db()
    conn.execute(
        "INSERT OR REPLACE INTO config (key, value) VALUES ('wa_connection_state', ?)",
        (state,)
    )
    conn.commit()
    conn.close()
