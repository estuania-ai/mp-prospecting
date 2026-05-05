"""
Job de seguimiento automatico para leads enviados sin respuesta
- 24 horas sin respuesta: mensaje 1 de seguimiento
- 72 horas sin respuesta: mensaje 2 de seguimiento (cierre suave)
Solo aplica a leads con estado 'enviado' (sin cambio de estado)
"""
import logging
from datetime import datetime
from database import get_db

logger = logging.getLogger(__name__)

MSG_24H = "Hola {nombre}! Como estas? Te escribo rapidito para saber si pudiste darle una mirada a la imagen que te mande el otro dia. Me encantaria que comparemos juntos. Avisame si tienes un tiempo para llamarte, la idea es ver de forma transparente si realmente te conviene el cambio. Un abrazo"

MSG_72H = "Hola {nombre}! Te escribo cortito para no quitarte tiempo ni ser invasivo. Si mas adelante te animas a probar, me avisas y lo revisamos. Que tengas un lindo dia. Saludos"


def get_leads_para_seguimiento(horas: int, tipo: str) -> list:
    conn = get_db()
    rows = conn.execute(f'''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro,
               m.sent_at,
               CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas_desde_envio
        FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        JOIN messages m ON l.id = m.lead_id
        LEFT JOIN opt_out o ON l.phone = o.phone
        WHERE ls.status = 'enviado'
          AND m.status = 'sent'
          AND m.message_type IN ('prospecting', 'manual')
          AND o.phone IS NULL
          AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= ?
          AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) < ?
          AND l.phone NOT IN (
              SELECT DISTINCT phone FROM messages
              WHERE message_type = 'seguimiento_{tipo}'
              AND status = 'sent'
          )
        GROUP BY l.id
        ORDER BY m.sent_at ASC
    ''', (horas,)).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def register_seguimiento(lead: dict, tipo: str, success: bool):
    conn = get_db()
    conn.execute('''
        INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
        VALUES (?, ?, ?, ?, datetime('now','localtime'), ?, ?)
    ''', (
        lead['id'], lead['phone'],
        f'seguimiento_{tipo}',
        'sent' if success else 'failed',
        lead.get('rubro', ''), lead.get('comuna', '')
    ))
    if success:
        # Actualizar columna seguimiento en leads
        if tipo == '24h':
            conn.execute("""
                UPDATE leads SET seguimiento_24h=1, 
                seguimiento_24h_fecha=datetime('now','localtime')
                WHERE id=?
            """, (lead['id'],))
        elif tipo == '72h':
            conn.execute("""
                UPDATE leads SET seguimiento_72h=1,
                seguimiento_72h_fecha=datetime('now','localtime')
                WHERE id=?
            """, (lead['id'],))
    conn.commit()
    conn.close()


def run_seguimiento():
    logger.info(f"[SEGUIMIENTO] Iniciando - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    # Preferir Evolution API (Railway) - sin popups en la PC del usuario
    from whatsapp import evolution_client as ev
    use_evolution = ev.is_connected()

    sender = None
    human_delay = None
    if not use_evolution:
        logger.warning("[SEGUIMIENTO] Evolution API no conectada — fallback sender_desktop (popup WhatsApp Web)")
        try:
            from whatsapp.sender_desktop import get_sender, human_delay as _hd
            human_delay = _hd
            sender = get_sender()
            if not sender._is_logged_in:
                sender.start()
        except Exception as e:
            logger.error(f"[SEGUIMIENTO] No se pudo iniciar sender de escritorio: {e}")
            return
    else:
        logger.info("[SEGUIMIENTO] Usando Evolution API (envío silencioso desde Railway)")
        # Para los delays cuando usamos Evolution, hacemos sleep simple
        import time as _time, random as _random
        def human_delay():
            _time.sleep(_random.uniform(30, 60))

    def _send(phone, msg):
        if use_evolution:
            r = ev.send_message(phone, msg, None)
            return {'success': r.get('ok', False)}
        return sender.send_message(phone, msg, None)

    total_24h = 0
    total_72h = 0

    # Mensaje 24 horas
    leads_24h = get_leads_para_seguimiento(24, '24h')
    logger.info(f"[SEGUIMIENTO] 24h: {len(leads_24h)} leads pendientes")
    for lead in leads_24h:
        msg = MSG_24H.format(nombre=lead['name'])
        result = _send(lead['phone'], msg)
        register_seguimiento(lead, '24h', result['success'])
        if result['success']:
            total_24h += 1
            logger.info(f"[SEGUIMIENTO 24h] OK - {lead['name']}")
        if lead != leads_24h[-1]:
            human_delay()

    # Mensaje 72 horas
    leads_72h = get_leads_para_seguimiento(72, '72h')
    logger.info(f"[SEGUIMIENTO] 72h: {len(leads_72h)} leads pendientes")
    for lead in leads_72h:
        msg = MSG_72H.format(nombre=lead['name'])
        result = _send(lead['phone'], msg)
        register_seguimiento(lead, '72h', result['success'])
        if result['success']:
            total_72h += 1
            logger.info(f"[SEGUIMIENTO 72h] OK - {lead['name']}")
        if lead != leads_72h[-1]:
            human_delay()

    total_enviados = total_24h + total_72h

    # Registrar en campanas si hubo envios
    if total_enviados > 0:
        conn = get_db()
        if total_24h > 0:
            conn.execute('''
                INSERT INTO campaigns (name, total_sent, sent_at, status)
                VALUES (?, ?, datetime('now','localtime'), 'completed')
            ''', (f"Seguimiento 24h {datetime.now().strftime('%d/%m/%Y %H:%M')}", total_24h))
        if total_72h > 0:
            conn.execute('''
                INSERT INTO campaigns (name, total_sent, sent_at, status)
                VALUES (?, ?, datetime('now','localtime'), 'completed')
            ''', (f"Seguimiento 72h {datetime.now().strftime('%d/%m/%Y %H:%M')}", total_72h))
        conn.commit()
        conn.close()

    logger.info(f"[SEGUIMIENTO] Completado: {total_24h} msgs 24h + {total_72h} msgs 72h")
