"""
Ruta para envio manual de mensajes desde la pestaña Leads
Respeta todas las reglas anti-spam: validacion de telefono, horario permitido, deduplicacion, exclusion de landlines
"""
from flask import Blueprint, request, jsonify
from database import get_db, get_config
import threading
import logging
import re
from datetime import datetime

logger = logging.getLogger(__name__)
manual_bp = Blueprint('manual', __name__)


# ── PROTECCIONES ANTI-SPAM (importadas de send_prospecting.py)
ALLOWED_SEND_HOURS = (7, 20)  # 07:00 a 20:00


def is_valid_phone(phone: str) -> bool:
    """
    Valida que sea número móvil chileno válido para WhatsApp.
    - RECHAZA: 562XXXXXXX (números fijos/landlines - no soportan WhatsApp)
    - ACEPTA: 569XXXXXXX (celulares - 9 dígitos)
    """
    if not phone:
        return False
    phone = phone.strip().replace(' ', '').replace('-', '')

    # RECHAZA números fijos que comienzan con 562
    if re.match(r'^(\+?56)?2\d{8}$', phone):
        return False  # Número fijo (landline), no soporta WhatsApp

    # ACEPTA solo celulares: +56 o 56 seguido de 9 dígitos (comienzan con 9)
    return bool(re.match(r'^(\+?56)?9\d{8}$', phone))


def is_allowed_send_hour() -> bool:
    """Verifica que la hora actual esté en el rango permitido"""
    current_hour = datetime.now().hour
    return ALLOWED_SEND_HOURS[0] <= current_hour < ALLOWED_SEND_HOURS[1]


def has_message_today(lead_id: int, message_type: str = 'manual') -> bool:
    """Verifica si el lead ya recibió un mensaje hoy del tipo indicado"""
    conn = get_db()
    today = datetime.now().strftime('%Y-%m-%d')
    existing = conn.execute('''
        SELECT COUNT(*) as cnt FROM messages
        WHERE lead_id = ? AND message_type = ?
          AND date(sent_at) = ?
    ''', (lead_id, message_type, today)).fetchone()
    conn.close()

    return existing and existing['cnt'] > 0


def _send_manual_batch(lead_ids: list, batch_name: str = "Manual"):
    """Ejecuta envio manual en hilo separado con validaciones anti-spam"""
    from rubros_config import get_mensaje, get_imagen_url
    from database import get_db

    # ── PROTECCIÓN: Verificar horario permitido
    current_time = datetime.now().strftime('%H:%M')
    if not is_allowed_send_hour():
        logger.warning(f"[{batch_name}] ❌ BLOQUEADO: Intento de envío a las {current_time} (solo permitido 07:00-20:00)")
        return

    conn = get_db()
    placeholders = ','.join('?' * len(lead_ids))
    leads = conn.execute(f'''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro
        FROM leads l
        LEFT JOIN opt_out o ON l.phone = o.phone
        WHERE l.id IN ({placeholders})
        AND o.phone IS NULL
    ''', lead_ids).fetchall()
    conn.close()

    if not leads:
        logger.info(f"[{batch_name}] Sin leads validos para enviar")
        return

    leads = [dict(r) for r in leads]

    # ── Filtrar: validar telefonos, excluir landlines, verificar dedup ──
    valid_leads = []
    for lead in leads:
        if not is_valid_phone(lead['phone']):
            logger.warning(f"[{batch_name}] ❌ {lead['name']} ({lead['phone']}) - Teléfono inválido o landline (rechazado)")
            continue
        if has_message_today(lead['id'], 'manual'):
            logger.warning(f"[{batch_name}] ⚠ {lead['name']} ({lead['phone']}) - Ya recibió mensaje hoy (deduplicación)")
            continue
        valid_leads.append(lead)

    if not valid_leads:
        logger.info(f"[{batch_name}] Sin leads válidos después de validaciones anti-spam")
        return

    logger.info(f"[{batch_name}] Iniciando envio de {len(valid_leads)}/{len(leads)} mensajes válidos")

    # ── Usar Evolution API si está conectada, sino fallback a sender_desktop ──
    import time, random
    from whatsapp import evolution_client as ev
    use_evolution = ev.is_connected()

    sender = None
    if use_evolution:
        logger.info(f"[{batch_name}] Usando Evolution API")
    else:
        logger.info(f"[{batch_name}] Evolution API no disponible — usando sender de escritorio")
        try:
            from whatsapp.sender_desktop import get_sender
            sender = get_sender()
            if not sender._is_logged_in:
                sender.start()
        except Exception as e:
            logger.error(f"[{batch_name}] No se pudo iniciar sender de escritorio: {e}")
            return

    conn_cfg = get_db()
    delay_min = int(conn_cfg.execute("SELECT value FROM config WHERE key='wa_delay_min_sec'").fetchone()[0] or 15)
    delay_max = int(conn_cfg.execute("SELECT value FROM config WHERE key='wa_delay_max_sec'").fetchone()[0] or 35)
    conn_cfg.close()

    sent = failed = no_phone = 0
    for i, lead in enumerate(valid_leads):
        try:
            msg = get_mensaje(lead['rubro'], lead['name'], lead.get('comuna', ''))
            img = get_imagen_url(lead['rubro'])

            if use_evolution:
                result = ev.send_message(lead['phone'], msg, img)
                ok = result.get('ok', False)
                error_msg = result.get('error', '')
            else:
                result = sender.send_message(lead['phone'], msg, img)
                ok = result.get('success', False)
                error_msg = result.get('error', '')

            conn2 = get_db()
            if ok:
                status = 'sent'
                sent += 1
            elif 'phone' in str(error_msg).lower():
                status = 'phone_not_exists'
                no_phone += 1
            else:
                status = 'failed'
                failed += 1

            conn2.execute('''
                INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
                VALUES (?, ?, 'manual', ?, datetime('now','localtime'), ?, ?)
            ''', (lead['id'], lead['phone'], status, lead['rubro'], lead.get('comuna', '')))

            if ok:
                conn2.execute('''
                    INSERT INTO lead_status (lead_id, status, updated_at)
                    VALUES (?, 'enviado', datetime('now','localtime'))
                    ON CONFLICT(lead_id) DO UPDATE SET
                        status = 'enviado',
                        updated_at = excluded.updated_at
                ''', (lead['id'],))

            conn2.commit()
            conn2.close()

            logger.info(f"[{batch_name}] [{i+1}/{len(valid_leads)}] {lead['name']} ({lead['phone']}) rubro={lead['rubro']} → {'✓ OK' if ok else '✗ FAIL'}")

            # Delay anti-bloqueo entre mensajes
            if i < len(valid_leads) - 1:
                time.sleep(random.uniform(delay_min, delay_max))

        except Exception as e:
            failed += 1
            logger.error(f"[{batch_name}] Error enviando a {lead['name']}: {e}")

    logger.info(f"[{batch_name}] Completado: {sent} enviados, {no_phone} sin tel, {failed} fallidos")


@manual_bp.route('/send', methods=['POST'])
def manual_send():
    """Envía WhatsApp manual a leads seleccionados"""
    data = request.json or {}
    lead_ids = data.get('lead_ids', [])

    if not lead_ids:
        return jsonify({'error': 'No se seleccionaron leads'}), 400
    if len(lead_ids) > 50:
        return jsonify({'error': 'Maximo 50 leads por envio manual'}), 400

    # Verificar horario permitido antes de lanzar
    if not is_allowed_send_hour():
        hora = datetime.now().strftime('%H:%M')
        return jsonify({'error': f'⏰ Envíos bloqueados fuera de horario. Permitido: 07:00-20:00. Hora actual: {hora}'}), 403

    # Lanzar en hilo — usa Evolution API automáticamente
    t = threading.Thread(target=_send_manual_batch, args=(lead_ids, "Manual"))
    t.daemon = True
    t.start()

    return jsonify({
        'ok': True,
        'message': f'Enviando {len(lead_ids)} mensajes en segundo plano. Los estados se actualizan automaticamente. Se respetan todas las reglas anti-spam.',
        'total': len(lead_ids)
    })


@manual_bp.route('/send-by-rubro', methods=['POST'])
def send_by_rubro():
    """
    Envía WhatsApp manual a todos los leads de un rubro específico.
    Respeta: validación de teléfono, horario permitido, deduplicación, exclusión de landlines
    """
    data = request.json or {}
    rubro = data.get('rubro', '').strip()

    if not rubro:
        return jsonify({'error': 'Rubro requerido'}), 400

    # ── PROTECCIÓN: Verificar horario permitido
    current_time = datetime.now().strftime('%H:%M')
    if not is_allowed_send_hour():
        return jsonify({
            'error': f'❌ Envios bloqueados. Horario permitido: 07:00-20:00. Hora actual: {current_time}'
        }), 403

    conn = get_db()
    leads = conn.execute(f'''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro
        FROM leads l
        LEFT JOIN opt_out o ON l.phone = o.phone
        WHERE l.rubro = ? AND o.phone IS NULL
    ''', (rubro,)).fetchall()
    conn.close()

    if not leads:
        return jsonify({'error': f'No hay leads activos para el rubro: {rubro}'}), 404

    leads = [dict(r) for r in leads]

    # ── Filtrar: validar teléfonos, excluir landlines
    valid_leads = []
    skipped_invalid = 0
    for lead in leads:
        if not is_valid_phone(lead['phone']):
            skipped_invalid += 1
            continue
        valid_leads.append(lead)

    if not valid_leads:
        return jsonify({
            'error': f'Todos los leads del rubro {rubro} tienen teléfonos inválidos o landlines',
            'skipped': skipped_invalid
        }), 400

    # Lanzar en hilo — usa Evolution API automáticamente
    batch_name = f"ByRubro_{rubro}"
    t = threading.Thread(target=_send_manual_batch, args=(
        [lead['id'] for lead in valid_leads],
        batch_name
    ))
    t.daemon = True
    t.start()

    return jsonify({
        'ok': True,
        'message': f'Enviando {len(valid_leads)} mensajes del rubro "{rubro}" en segundo plano',
        'rubro': rubro,
        'total_selected': len(valid_leads),
        'skipped_invalid': skipped_invalid,
        'note': 'Se respetan todas las reglas anti-spam: validación de teléfono, horario permitido (07:00-20:00), deduplicación y exclusión de landlines'
    })


@manual_bp.route('/rubros', methods=['GET'])
def get_rubros():
    """Retorna lista de todos los rubros disponibles para filtrar"""
    try:
        from rubros_config import RUBROS
        rubros = [
            {
                'key': key,
                'label': config['label'],
                'emoji': config['emoji'],
                'categoria': config['categoria']
            }
            for key, config in RUBROS.items()
        ]
        return jsonify({'rubros': sorted(rubros, key=lambda x: x['label'])})
    except Exception as e:
        logger.error(f"Error obteniendo rubros: {e}")
        return jsonify({'error': 'Error obteniendo lista de rubros'}), 500


@manual_bp.route('/leads-by-rubro/<rubro>', methods=['GET'])
def get_leads_by_rubro(rubro: str):
    """Retorna lista de leads válidos para un rubro específico (sin teléfonos inválidos)"""
    conn = get_db()
    leads = conn.execute(f'''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro
        FROM leads l
        LEFT JOIN opt_out o ON l.phone = o.phone
        WHERE l.rubro = ? AND o.phone IS NULL
        ORDER BY l.name ASC
    ''', (rubro,)).fetchall()
    conn.close()

    if not leads:
        return jsonify({'leads': [], 'total': 0, 'valid': 0})

    leads = [dict(r) for r in leads]

    # Filtrar válidos: números móviles, no landlines
    valid_leads = []
    invalid_count = 0
    for lead in leads:
        if is_valid_phone(lead['phone']):
            valid_leads.append({
                **lead,
                'valid': True
            })
        else:
            invalid_count += 1

    return jsonify({
        'leads': valid_leads,
        'total': len(leads),
        'valid': len(valid_leads),
        'invalid': invalid_count,
        'rubro': rubro
    })


@manual_bp.route('/status', methods=['GET'])
def send_status():
    """Retorna el estado actual del sender — prioriza Evolution API"""
    try:
        from whatsapp import evolution_client as ev
        connected = ev.is_connected()
        return jsonify({
            'logged_in': connected,
            'source': 'evolution',
            'allowed_hours': f"{ALLOWED_SEND_HOURS[0]:02d}:00 - {ALLOWED_SEND_HOURS[1]:02d}:00"
        })
    except Exception:
        return jsonify({
            'logged_in': False,
            'source': 'evolution',
            'allowed_hours': f"{ALLOWED_SEND_HOURS[0]:02d}:00 - {ALLOWED_SEND_HOURS[1]:02d}:00"
        })
