"""
Job de fidelizacion de sellers - ejecutado por scheduler_local.py
Envia mensajes segun dias desde que el seller fue cerrado:
  Dia 7:  Activacion y Liquidez
  Dia 14: Potenciar Ventas
  Dia 15: Seguimiento
  Dia 30: Gestion y Seguridad
  Dia 35: Fidelizacion y Upselling
"""

import logging
from datetime import datetime
from database import get_db
from fidelizacion_config import ETAPAS, get_fidelizacion_mensaje
from rubros_config import RUBROS, RUBRO_LABEL_TO_KEY

logger = logging.getLogger(__name__)


def get_categoria_from_rubro(rubro: str) -> str:
    """Obtiene la categoria a partir del rubro key o label"""
    rubro_lower = rubro.lower().strip() if rubro else ''
    rubro_key = RUBRO_LABEL_TO_KEY.get(rubro_lower, rubro_lower)
    rubro_data = RUBROS.get(rubro_key, {})
    return rubro_data.get('categoria', '')


def get_sellers_para_etapa(dias: int) -> list:
    """Retorna sellers que deben recibir mensaje de la etapa correspondiente a N dias"""
    conn = get_db()
    rows = conn.execute('''
        SELECT
            s.id, s.name, s.phone, s.rubro, s.categoria,
            s.closed_at, s.active,
            julianday('now','localtime') - julianday(s.closed_at) as dias_desde_cierre
        FROM sellers s
        LEFT JOIN opt_out o ON s.phone = o.phone
        WHERE s.active = 1
          AND o.phone IS NULL
          AND s.closed_at IS NOT NULL
          AND CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) = ?
          AND s.phone NOT IN (
              SELECT DISTINCT phone FROM messages
              WHERE message_type = 'fidelizacion'
              AND rubro = ?
          )
        ORDER BY s.closed_at ASC
    ''', (dias, f'etapa_{dias}')).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_all_sellers_pendientes() -> list:
    """Retorna todos los sellers con etapas pendientes de envio"""
    conn = get_db()

    pendientes = []
    for dias, etapa_key, etapa_nombre in ETAPAS:
        rows = conn.execute('''
            SELECT
                s.id, s.name, s.phone, s.rubro, s.categoria,
                s.closed_at,
                CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) as dias_desde_cierre,
                ? as etapa_key,
                ? as etapa_nombre,
                ? as etapa_dias
            FROM sellers s
            LEFT JOIN opt_out o ON s.phone = o.phone
            WHERE s.active = 1
              AND o.phone IS NULL
              AND s.closed_at IS NOT NULL
              AND CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) >= ?
              AND s.phone NOT IN (
                  SELECT DISTINCT phone FROM messages
                  WHERE message_type = 'fidelizacion'
                  AND rubro = ?
              )
        ''', (etapa_key, etapa_nombre, dias, dias, f'etapa_{dias}')).fetchall()

        for r in rows:
            pendientes.append(dict(r))

    conn.close()
    return pendientes


def register_fidelizacion(seller: dict, etapa_dias: int, success: bool):
    conn = get_db()
    conn.execute('''
        INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
        VALUES (?, ?, 'fidelizacion', ?, datetime('now','localtime'), ?, ?)
    ''', (
        seller.get('id'),
        seller.get('phone'),
        'sent' if success else 'failed',
        f'etapa_{etapa_dias}',
        seller.get('comuna', '')
    ))
    conn.commit()
    conn.close()


def run_fidelizacion():
    """Job principal - detecta y envia mensajes segun etapa de cada seller"""
    logger.info(f"[FIDELIZACION] Iniciando - {datetime.now().strftime('%Y-%m-%d %H:%M')}")

    conn = get_db()
    sellers = conn.execute('''
        SELECT
            s.id, s.name, s.phone, s.rubro, s.categoria,
            s.closed_at,
            CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) as dias
        FROM sellers s
        LEFT JOIN opt_out o ON s.phone = o.phone
        WHERE s.active = 1
          AND o.phone IS NULL
          AND s.closed_at IS NOT NULL
        ORDER BY s.closed_at ASC
    ''').fetchall()
    conn.close()

    if not sellers:
        logger.info("[FIDELIZACION] Sin sellers activos")
        return

    # Preferir Evolution API (sin popups en la PC del usuario)
    from whatsapp import evolution_client as ev
    use_evolution = ev.is_connected()

    sender = None
    if not use_evolution:
        logger.warning("[FIDELIZACION] Evolution API no conectada — fallback sender_desktop (popup WhatsApp Web)")
        try:
            from whatsapp.sender_desktop import get_sender
            sender = get_sender()
            if not sender._is_logged_in:
                sender.start()
        except Exception as e:
            logger.error(f"[FIDELIZACION] No se pudo iniciar sender de escritorio: {e}")
            return
    else:
        logger.info("[FIDELIZACION] Usando Evolution API (envío silencioso)")

    def _send(phone, msg):
        if use_evolution:
            r = ev.send_message(phone, msg, None)
            return {'success': r.get('ok', False), 'error': r.get('error', '')}
        return sender.send_message(phone, msg, None)

    enviados = 0
    for seller in sellers:
        s = dict(seller)
        dias = s.get('dias', 0)

        # Buscar si hay etapa para hoy exacto
        etapa = None
        for d, key, nombre in ETAPAS:
            if dias == d:
                etapa = (d, key, nombre)
                break

        if not etapa:
            continue

        dias_e, etapa_key, etapa_nombre = etapa

        # Verificar si ya se envio esta etapa
        conn2 = get_db()
        ya_enviado = conn2.execute('''
            SELECT COUNT(*) FROM messages
            WHERE phone = ? AND message_type = 'fidelizacion'
            AND rubro = ? AND status = 'sent'
        ''', (s['phone'], f'etapa_{dias_e}')).fetchone()[0]
        conn2.close()

        if ya_enviado:
            logger.info(f"[FIDELIZACION] {s['name']} - etapa {etapa_nombre} ya enviada")
            continue

        # Obtener categoria y mensaje
        categoria = s.get('categoria', '') or get_categoria_from_rubro(s.get('rubro', ''))
        mensaje = get_fidelizacion_mensaje(categoria, etapa_key)

        if not mensaje:
            logger.warning(f"[FIDELIZACION] Sin mensaje para categoria '{categoria}' etapa '{etapa_key}'")
            continue

        logger.info(f"[FIDELIZACION] {s['name']} | Dia {dias_e} | {etapa_nombre} | Cat: {categoria}")

        result = _send(s['phone'], mensaje)
        register_fidelizacion(s, dias_e, result['success'])

        if result['success']:
            enviados += 1
            logger.info(f"[FIDELIZACION] OK - {s['name']}")
        else:
            logger.warning(f"[FIDELIZACION] FAIL - {s['name']}: {result.get('error')}")

    logger.info(f"[FIDELIZACION] Completado: {enviados} mensajes enviados")
