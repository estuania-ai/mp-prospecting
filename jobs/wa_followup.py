"""
Job: Follow-up WhatsApp automático.
Se ejecuta cada día a las 10:00.

Lógica:
  1. Busca contactos de email (et_contacts) que:
     - Recibieron email hace más de N días (configurado en wa_followup_days)
     - No han respondido (estado_interes = 'pendiente' o 'sin_respuesta')
     - No tienen opt_out
     - No recibieron ya un WA de follow-up
  2. Envía mensaje WhatsApp de seguimiento via Evolution API
  3. Registra en wa_messages
"""

import logging
import os
from datetime import datetime, timedelta

from database import get_db
from whatsapp import evolution_client as ev

logger = logging.getLogger(__name__)

# Plantilla por defecto (se puede personalizar por rubro en el futuro)
_FOLLOWUP_TEMPLATE = """Hola {nombre} 👋

Te escribo de MercadoPago. Hace unos días te envié un email sobre cómo podemos ayudarte a aceptar más medios de pago en tu {rubro}.

¿Tuviste la oportunidad de revisarlo?

Si quieres te cuento en 2 minutos cómo funciona.

Saludos,
{exec_name}"""


def _get_config(conn, key: str, default: str = "") -> str:
    row = conn.execute("SELECT value FROM config WHERE key=?", (key,)).fetchone()
    return row[0] if row else default


def run_wa_followup() -> dict:
    """
    Ejecuta el follow-up WhatsApp para contactos email sin respuesta.
    Retorna dict con métricas.
    """
    if not ev.is_connected():
        logger.warning("[WA Follow-up] Evolution API no conectada. Saltando.")
        return {"ok": False, "reason": "wa_not_connected", "sent": 0}

    conn = get_db()

    followup_days  = int(_get_config(conn, 'wa_followup_days',  '3'))
    daily_limit    = int(_get_config(conn, 'wa_daily_limit',    '150'))
    delay_min      = int(_get_config(conn, 'wa_delay_min_sec',  '30'))
    delay_max      = int(_get_config(conn, 'wa_delay_max_sec',  '60'))
    enabled        = _get_config(conn, 'wa_followup_enabled', '1') == '1'
    exec_name      = _get_config(conn, 'exec_name', 'Juan')

    if not enabled:
        conn.close()
        logger.info("[WA Follow-up] Desactivado en config.")
        return {"ok": True, "reason": "disabled", "sent": 0}

    cutoff_date = (datetime.now() - timedelta(days=followup_days)).strftime('%Y-%m-%d')

    # Contactos candidatos:
    # - tienen teléfono
    # - email enviado hace > N días
    # - no respondieron
    # - no tienen opt_out
    # - no recibieron WA follow-up ya
    candidates = conn.execute("""
        SELECT ec.id, ec.business_name, ec.phone, ec.rubro, ec.fecha_envio
        FROM et_contacts ec
        WHERE ec.phone IS NOT NULL
          AND ec.phone != ''
          AND ec.opt_out = 0
          AND (ec.estado_interes = 'pendiente' OR ec.estado_interes IS NULL)
          AND ec.fecha_envio IS NOT NULL
          AND date(ec.fecha_envio) <= ?
          AND ec.id NOT IN (
              SELECT et_contact_id FROM wa_messages
              WHERE et_contact_id IS NOT NULL
                AND message_type = 'followup_email'
          )
        ORDER BY ec.fecha_envio ASC
        LIMIT ?
    """, (cutoff_date, daily_limit)).fetchall()

    conn.close()

    total     = len(candidates)
    sent      = 0
    errors    = 0
    import time, random

    logger.info(f"[WA Follow-up] {total} candidatos para follow-up WA")

    for contact in candidates:
        cid       = contact['id']
        nombre    = (contact['business_name'] or 'estimado/a').split()[0]
        phone     = contact['phone']
        rubro     = contact['rubro'] or 'negocio'

        message = _FOLLOWUP_TEMPLATE.format(
            nombre    = nombre,
            rubro     = rubro,
            exec_name = exec_name,
        )

        result = ev.send_message(phone, message)

        # Guardar en wa_messages
        db = get_db()
        db.execute("""
            INSERT INTO wa_messages
                (phone, message_text, status, wa_message_id, message_type,
                 rubro, et_contact_id, sent_at, source)
            VALUES (?, ?, ?, ?, 'followup_email', ?, ?, ?, 'evolution')
        """, (
            phone, message,
            'sent' if result['ok'] else 'failed',
            result.get('data', {}).get('key', {}).get('id'),
            rubro, cid,
            datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        ))

        # Marcar seguimiento en et_contacts
        if result['ok']:
            db.execute("""
                UPDATE et_contacts
                SET estado_interes = 'followup_wa_enviado'
                WHERE id = ?
            """, (cid,))
            sent += 1
        else:
            errors += 1
            logger.warning(f"[WA Follow-up] Fallo enviando a {phone}: {result.get('error')}")

        db.commit()
        db.close()

        # Delay anti-bloqueo
        if sent < total:
            delay = random.uniform(delay_min, delay_max)
            logger.info(f"[WA Follow-up] Enviado {sent}/{total} — esperando {delay:.0f}s")
            time.sleep(delay)

    logger.info(f"[WA Follow-up] Completado: {sent} enviados, {errors} errores")
    return {"ok": True, "sent": sent, "errors": errors, "total_candidates": total}
