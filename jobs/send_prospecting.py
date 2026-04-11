"""
Job de prospeccion diaria - 3 lotes L-V
Lote 1: 15 mensajes a las 09:30
Lote 2: 10 mensajes a las 15:00
Lote 3: 15 mensajes a las 17:30
Total: 40 mensajes diarios
"""

import logging
from datetime import datetime
from database import get_db, get_config
from rubros_config import get_mensaje, get_imagen_url

logger = logging.getLogger(__name__)


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
    return [dict(r) for r in rows]


def build_message(contact: dict) -> str:
    nombre    = contact.get('name', 'estimado/a')
    rubro_key = contact.get('rubro', 'almacen')
    comuna    = contact.get('comuna', '')
    return get_mensaje(rubro_key, nombre, comuna)


def build_image_url(contact: dict) -> str | None:
    return get_imagen_url(contact.get('rubro', ''))


def register_send(contact: dict, success: bool, error: str = None):
    conn = get_db()
    status = 'sent' if success else 'failed'
    if error == 'phone_not_exists':
        status = 'phone_not_exists'

    conn.execute('''
        INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
        VALUES (?, ?, 'prospecting', ?, datetime('now','localtime'), ?, ?)
    ''', (
        contact.get('id'), contact.get('phone'), status,
        contact.get('rubro'), contact.get('comuna')
    ))

    lead_status = 'enviado' if success else ('telefono_no_existe' if error == 'phone_not_exists' else 'no_enviado')
    conn.execute('''
        INSERT INTO lead_status (lead_id, status, updated_at)
        VALUES (?, ?, datetime('now','localtime'))
        ON CONFLICT(lead_id) DO UPDATE SET
            status = excluded.status,
            updated_at = excluded.updated_at
    ''', (contact.get('id'), lead_status))

    conn.commit()
    conn.close()


def run_prospecting_batch(limit: int, batch_name: str = ""):
    logger.info(f"[PROSPECCION {batch_name}] Iniciando - {limit} mensajes - {datetime.now().strftime('%H:%M')}")

    leads = get_pending_leads(limit)
    if not leads:
        logger.info(f"[{batch_name}] Sin leads pendientes")
        return

    logger.info(f"[{batch_name}] {len(leads)} leads encontrados")

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

    logger.info(f"[{batch_name}] Completado: {sent} enviados, {no_phone} sin telefono, {failed} fallidos")

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
