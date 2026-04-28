"""
Job: Seguimiento automático WhatsApp para leads WA en estado 'enviado'.
Se ejecuta periódicamente (cada 2 horas L-V fuera de ventanas de prospección).

Lógica:
  1. Leads en estado 'enviado' hace >= 24h sin seguimiento 24h → MSG_24H
  2. Leads en estado 'enviado' hace >= 72h sin seguimiento 72h → MSG_72H
  3. Respeta ventanas anti-spam: no envía ±15 min de 09:30 / 15:00 / 17:30
  4. Solo L-V (lunes a viernes)
  5. Usa Evolution API; si no está conectado, sale sin error
"""

import logging
import time
import random
from datetime import datetime, timedelta
from database import get_db

logger = logging.getLogger(__name__)

MSG_24H = (
    "Hola {nombre}! ¿Cómo estás? "
    "Te escribo rapidito para saber si pudiste ver la imagen que te mandé el otro día. "
    "Me gustaría comparar juntos. "
    "Avísame si tienes un minuto y te llamo. ¡Saludos!"
)

MSG_72H = (
    "Hola {nombre}! Te escribo cortito para no quitarte tiempo. "
    "Si más adelante quieres conocer más sobre MercadoPago POS, me avisas. "
    "¡Que tengas un lindo día!"
)

# Ventanas de prospección (hora, minuto) ± GRACE_MINUTES
_PROSPECCION_WINDOWS = [(9, 30), (15, 0), (17, 30)]
_GRACE_MINUTES = 15


def _en_ventana_prospeccion() -> bool:
    """Retorna True si ahora está dentro de una ventana de prospección ±15 min."""
    now = datetime.now()
    for h, m in _PROSPECCION_WINDOWS:
        window_start = now.replace(hour=h, minute=m, second=0, microsecond=0) - timedelta(minutes=_GRACE_MINUTES)
        window_end   = now.replace(hour=h, minute=m, second=0, microsecond=0) + timedelta(minutes=_GRACE_MINUTES)
        if window_start <= now <= window_end:
            return True
    return False


def _es_dia_laboral() -> bool:
    """Lunes(0)–Viernes(4)"""
    return datetime.now().weekday() < 5


def _get_leads_seguimiento(horas_min: int, horas_max: int | None, tipo: str) -> list:
    """
    Leads en estado 'enviado' hace horas_min <= horas < horas_max,
    sin mensaje de seguimiento del tipo indicado.
    """
    conn = get_db()
    if horas_max is not None:
        rows = conn.execute("""
            SELECT l.id, l.name, l.phone, l.rubro, l.comuna,
                   CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
            FROM leads l
            JOIN lead_status ls ON l.id = ls.lead_id
            JOIN messages m ON l.id = m.lead_id
                 AND m.message_type IN ('prospecting','manual')
                 AND m.status = 'sent'
            LEFT JOIN opt_out o ON l.phone = o.phone
            LEFT JOIN messages mseg ON l.id = mseg.lead_id
                 AND mseg.message_type = :seg_type
                 AND mseg.status = 'sent'
            WHERE ls.status = 'enviado'
              AND o.phone IS NULL
              AND mseg.id IS NULL
              AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= :hmin
              AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) < :hmax
            GROUP BY l.id
            ORDER BY m.sent_at ASC
            LIMIT 20
        """, {'seg_type': f'seguimiento_{tipo}', 'hmin': horas_min, 'hmax': horas_max}).fetchall()
    else:
        rows = conn.execute("""
            SELECT l.id, l.name, l.phone, l.rubro, l.comuna,
                   CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
            FROM leads l
            JOIN lead_status ls ON l.id = ls.lead_id
            JOIN messages m ON l.id = m.lead_id
                 AND m.message_type IN ('prospecting','manual')
                 AND m.status = 'sent'
            LEFT JOIN opt_out o ON l.phone = o.phone
            LEFT JOIN messages mseg ON l.id = mseg.lead_id
                 AND mseg.message_type = :seg_type
                 AND mseg.status = 'sent'
            WHERE ls.status = 'enviado'
              AND o.phone IS NULL
              AND mseg.id IS NULL
              AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= :hmin
            GROUP BY l.id
            ORDER BY m.sent_at ASC
            LIMIT 20
        """, {'seg_type': f'seguimiento_{tipo}', 'hmin': horas_min}).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def _registrar_seguimiento(lead: dict, tipo: str, success: bool):
    conn = get_db()
    conn.execute("""
        INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
        VALUES (?, ?, ?, ?, datetime('now','localtime'), ?, ?)
    """, (
        lead['id'], lead['phone'],
        f'seguimiento_{tipo}',
        'sent' if success else 'failed',
        lead.get('rubro', ''), lead.get('comuna', '')
    ))
    if success:
        col = 'seguimiento_24h' if tipo == '24h' else 'seguimiento_72h'
        col_fecha = f'{col}_fecha'
        try:
            conn.execute(
                f"UPDATE leads SET {col}=1, {col_fecha}=datetime('now','localtime') WHERE id=?",
                (lead['id'],)
            )
        except Exception:
            pass  # columna puede no existir en versiones antiguas
    conn.commit()
    conn.close()


def run_wa_seguimiento() -> dict:
    """
    Ejecuta el seguimiento WA para leads en estado 'enviado'.
    Respeta ventanas anti-spam y solo corre L-V.
    """
    if not _es_dia_laboral():
        logger.info("[WA Seguimiento] Fin de semana — saltando.")
        return {"ok": True, "reason": "weekend", "sent": 0}

    if _en_ventana_prospeccion():
        now_str = datetime.now().strftime('%H:%M')
        logger.info(f"[WA Seguimiento] Ventana de prospección activa ({now_str}) — saltando.")
        return {"ok": True, "reason": "prospeccion_window", "sent": 0}

    from whatsapp import evolution_client as ev
    if not ev.is_connected():
        logger.warning("[WA Seguimiento] Evolution API no conectada — saltando.")
        return {"ok": False, "reason": "wa_not_connected", "sent": 0}

    conn = get_db()
    delay_min = int((conn.execute("SELECT value FROM config WHERE key='wa_delay_min_sec'").fetchone() or [30])[0])
    delay_max = int((conn.execute("SELECT value FROM config WHERE key='wa_delay_max_sec'").fetchone() or [90])[0])
    conn.close()

    sent_24h = sent_72h = errors = 0

    # ── Seguimiento 24h (entre 24h y 72h sin respuesta) ─────────────
    leads_24h = _get_leads_seguimiento(24, 72, '24h')
    logger.info(f"[WA Seguimiento] 24h: {len(leads_24h)} leads pendientes")
    for i, lead in enumerate(leads_24h):
        nombre  = (lead.get('name') or 'estimado/a').split()[0]
        mensaje = MSG_24H.format(nombre=nombre)
        result  = ev.send_message(lead['phone'], mensaje)
        ok      = result.get('ok', False)
        _registrar_seguimiento(lead, '24h', ok)
        if ok:
            sent_24h += 1
            logger.info(f"[WA Seguimiento 24h] OK — {lead['name']} ({lead['horas']}h)")
        else:
            errors += 1
            logger.warning(f"[WA Seguimiento 24h] FAIL — {lead['phone']}: {result.get('error')}")
        if i < len(leads_24h) - 1:
            time.sleep(random.uniform(delay_min, delay_max))

    # ── Seguimiento 72h (más de 72h sin respuesta) ───────────────────
    leads_72h = _get_leads_seguimiento(72, None, '72h')
    logger.info(f"[WA Seguimiento] 72h: {len(leads_72h)} leads pendientes")
    for i, lead in enumerate(leads_72h):
        nombre  = (lead.get('name') or 'estimado/a').split()[0]
        mensaje = MSG_72H.format(nombre=nombre)
        result  = ev.send_message(lead['phone'], mensaje)
        ok      = result.get('ok', False)
        _registrar_seguimiento(lead, '72h', ok)
        if ok:
            sent_72h += 1
            logger.info(f"[WA Seguimiento 72h] OK — {lead['name']} ({lead['horas']}h)")
        else:
            errors += 1
            logger.warning(f"[WA Seguimiento 72h] FAIL — {lead['phone']}: {result.get('error')}")
        if i < len(leads_72h) - 1:
            time.sleep(random.uniform(delay_min, delay_max))

    total = sent_24h + sent_72h
    logger.info(f"[WA Seguimiento] Completado: {sent_24h} (24h) + {sent_72h} (72h) = {total} enviados, {errors} errores")
    return {"ok": True, "sent": total, "sent_24h": sent_24h, "sent_72h": sent_72h, "errors": errors}
