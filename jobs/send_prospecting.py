"""
Job de prospeccion diaria - 3 lotes L-V
Lote 1: 15 mensajes a las 09:30
Lote 2: 10 mensajes a las 15:00
Lote 3: 15 mensajes a las 17:30
Total: 40 mensajes diarios

PROTECCIONES CONTRA DUPLICADOS Y ENVÍOS INAPROPIADOS:
- Validación de teléfono antes de enviar (formato +56 o 56)
- Bloqueo de envíos fuera de horario permitido (07:00-20:00)
- Deduplicación de mensajes en la BD
"""

import logging
import re
from datetime import datetime
from database import get_db, get_config
from rubros_config import get_mensaje, get_imagen_url

logger = logging.getLogger(__name__)

# Horarios permitidos para envío (Santiago, Chile)
ALLOWED_SEND_HOURS = (7, 20)  # 07:00 a 20:00


def is_valid_phone(phone: str) -> bool:
    """
    Valida que sea número móvil chileno válido para WhatsApp.
    - RECHAZA: 562XXXXXXX (números fijos/landlines - no soportan WhatsApp)
    - ACEPTA: 569XXXXXXX (celulares - 9 dígitos)
    """
    if not phone:
        return False
    # Limpia espacios y guiones
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


def get_pending_leads(limit: int, offset: int = 0) -> list:
    conn = get_db()
    rows = conn.execute('''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro, l.address
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        LEFT JOIN opt_out o ON l.phone = o.phone
        WHERE o.phone IS NULL
          AND ls.status = 'no_enviado'
          AND l.phone IS NOT NULL
        ORDER BY ls.updated_at ASC NULLS FIRST
        LIMIT ? OFFSET ?
    ''', (limit, offset)).fetchall()
    conn.close()

    # Filtrar solo números válidos
    return [dict(r) for r in rows if is_valid_phone(r['phone'])]


def build_message(contact: dict) -> str:
    nombre    = contact.get('name', 'estimado/a')
    rubro_key = contact.get('rubro', 'almacen')
    comuna    = contact.get('comuna', '')
    return get_mensaje(rubro_key, nombre, comuna)


def build_image_url(contact: dict) -> str | None:
    return get_imagen_url(contact.get('rubro', ''))


def register_send(contact: dict, success: bool, error: str = None):
    conn = get_db()
    lead_id = contact.get('id')
    phone = contact.get('phone')

    # ── DEDUPLICACIÓN: Verifica si ya existe un mensaje hoy para este lead ──
    today = datetime.now().strftime('%Y-%m-%d')
    existing = conn.execute('''
        SELECT COUNT(*) as cnt FROM messages
        WHERE lead_id = ? AND message_type = 'prospecting'
          AND date(sent_at) = ?
    ''', (lead_id, today)).fetchone()

    if existing and existing['cnt'] > 0:
        logger.warning(f"[DEDUP] Ya existe mensaje hoy para lead {lead_id} ({phone}) - evitando duplicado")
        conn.close()
        return

    status = 'sent' if success else 'failed'
    if error == 'phone_not_exists':
        status = 'phone_not_exists'

    conn.execute('''
        INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
        VALUES (?, ?, 'prospecting', ?, datetime('now','localtime'), ?, ?)
    ''', (
        lead_id, phone, status,
        contact.get('rubro'), contact.get('comuna')
    ))

    lead_status = 'enviado' if success else ('telefono_no_existe' if error == 'phone_not_exists' else 'no_enviado')
    conn.execute('''
        INSERT INTO lead_status (lead_id, status, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
        ON CONFLICT(lead_id) DO UPDATE SET
            status = excluded.status,
            updated_at = excluded.updated_at
    ''', (lead_id, lead_status))

    conn.commit()
    conn.close()


def run_prospecting_batch(limit: int, batch_name: str = ""):
    import time, random
    current_time = datetime.now().strftime('%H:%M')
    logger.info(f"[PROSPECCION {batch_name}] Iniciando - {limit} mensajes - {current_time}")

    # ── PROTECCIÓN: Bloquear envíos fuera de horario permitido ──
    if not is_allowed_send_hour():
        logger.warning(f"[{batch_name}] ❌ BLOQUEADO: Intento de envío a las {current_time} (solo permitido 07:00-20:00)")
        return

    leads = get_pending_leads(limit)
    if not leads:
        logger.info(f"[{batch_name}] Sin leads pendientes")
        return

    logger.info(f"[{batch_name}] {len(leads)} leads encontrados (validados)")

    # ── Usar Evolution API (servidor) si está conectado,
    #    si no, intentar sender de escritorio como fallback ──────────
    from whatsapp import evolution_client as ev
    use_evolution = ev.is_connected()

    if not use_evolution:
        logger.warning(f"[{batch_name}] Evolution API no conectada — intentando sender de escritorio")
        try:
            from whatsapp.sender_desktop import get_sender
            sender = get_sender()
            if not sender._is_logged_in:
                sender.start()
            results = sender.send_batch(
                contacts=leads,
                get_message_fn=build_message,
                get_image_fn=build_image_url
            )
            sent = failed = no_phone = 0
            for r in results:
                contact = r.get('contact', {})
                error   = r.get('error', '')
                if r.get('success'):
                    register_send(contact, True)
                    sent += 1
                elif 'phone' in str(error).lower() or error == 'phone_not_exists':
                    register_send(contact, False, 'phone_not_exists')
                    no_phone += 1
                else:
                    register_send(contact, False, error)
                    failed += 1
            logger.info(f"[{batch_name}] (desktop) Completado: {sent} enviados, {no_phone} sin tel, {failed} fallidos")
        except Exception as e:
            logger.error(f"[{batch_name}] Sender de escritorio falló: {e}")
        return

    # ── Evolution API ─────────────────────────────────────────────
    conn = get_db()
    delay_min = int(conn.execute("SELECT value FROM config WHERE key='wa_delay_min_sec'").fetchone()[0] or 30)
    delay_max = int(conn.execute("SELECT value FROM config WHERE key='wa_delay_max_sec'").fetchone()[0] or 60)
    conn.close()

    sent = failed = no_phone = 0
    for i, contact in enumerate(leads):
        phone     = contact.get('phone', '')
        message   = build_message(contact)
        image_url = build_image_url(contact)

        result = ev.send_message(phone, message, image_url)
        ok     = result.get("ok", False)
        error  = result.get("error", "")

        register_send(contact, ok, None if ok else error)

        if ok:
            sent += 1
        elif 'phone' in str(error).lower():
            no_phone += 1
        else:
            failed += 1

        logger.info(f"[{batch_name}] [{i+1}/{len(leads)}] {phone} → {'OK' if ok else 'FAIL'}")

        # Delay anti-bloqueo entre mensajes
        if i < len(leads) - 1:
            delay = random.uniform(delay_min, delay_max)
            time.sleep(delay)

    logger.info(f"[{batch_name}] Completado: {sent} enviados, {no_phone} sin tel, {failed} fallidos")

    conn = get_db()
    conn.execute('''
        INSERT INTO campaigns (name, total_sent, sent_at, status)
        VALUES (?, ?, datetime('now','localtime'), 'completed')
    ''', (f"Lote {batch_name} {datetime.now().strftime('%d/%m/%Y %H:%M')}", sent))
    conn.commit()
    conn.close()


# Funciones llamadas por el scheduler
def run_batch1(): run_prospecting_batch(15, "09:30")
def run_batch2(): run_prospecting_batch(10, "15:00")
def run_batch3(): run_prospecting_batch(15, "17:30")

# Compatibilidad con llamada directa
def run_prospecting(): run_prospecting_batch(40, "manual")
