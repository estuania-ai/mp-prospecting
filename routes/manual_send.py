"""
Ruta para envio manual de mensajes desde la pestaña Leads
Respeta las reglas anti-spam y registra todo en BD
"""
from flask import Blueprint, request, jsonify
from database import get_db, get_config
import threading
import logging

logger = logging.getLogger(__name__)
manual_bp = Blueprint('manual', __name__)


def _send_manual_batch(lead_ids: list):
    """Ejecuta envio manual en hilo separado"""
    from rubros_config import get_mensaje, get_imagen_url
    from whatsapp.sender_desktop import get_sender
    from database import get_db

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
        logger.info("[MANUAL] Sin leads validos para enviar")
        return

    leads = [dict(r) for r in leads]
    logger.info(f"[MANUAL] Iniciando envio de {len(leads)} mensajes")

    sender = get_sender()
    if not sender._is_logged_in:
        sender.start()

    for i, lead in enumerate(leads):
        try:
            msg = get_mensaje(lead['rubro'], lead['name'])
            img = get_imagen_url(lead['rubro'])
            result = sender.send_message(lead['phone'], msg, img)

            conn2 = get_db()
            status = 'sent' if result['success'] else 'failed'
            conn2.execute('''
                INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
                VALUES (?, ?, 'manual', ?, datetime('now','localtime'), ?, ?)
            ''', (lead['id'], lead['phone'], status, lead['rubro'], lead.get('comuna', '')))

            if result['success']:
                conn2.execute('''
                    INSERT INTO lead_status (lead_id, status, updated_at)
                    VALUES (?, 'enviado', datetime('now','localtime'))
                    ON CONFLICT(lead_id) DO UPDATE SET
                        status = 'enviado',
                        updated_at = excluded.updated_at
                ''', (lead['id'],))

            conn2.commit()
            conn2.close()

            logger.info(f"[MANUAL] [{i+1}/{len(leads)}] {lead['name']} - {'OK' if result['success'] else 'FAIL'}")

        except Exception as e:
            logger.error(f"[MANUAL] Error enviando a {lead['name']}: {e}")


@manual_bp.route('/send', methods=['POST'])
def manual_send():
    data = request.json or {}
    lead_ids = data.get('lead_ids', [])

    if not lead_ids:
        return jsonify({'error': 'No se seleccionaron leads'}), 400
    if len(lead_ids) > 50:
        return jsonify({'error': 'Maximo 50 leads por envio manual'}), 400

    # Verificar que WhatsApp esta disponible
    try:
        from whatsapp.sender_desktop import get_sender
        sender = get_sender()
    except Exception as e:
        return jsonify({'error': f'Error iniciando WhatsApp: {e}'}), 500

    # Lanzar en hilo para no bloquear Flask
    t = threading.Thread(target=_send_manual_batch, args=(lead_ids,))
    t.daemon = True
    t.start()

    return jsonify({
        'ok': True,
        'message': f'Enviando {len(lead_ids)} mensajes en segundo plano. Los estados se actualizan automaticamente.',
        'total': len(lead_ids)
    })


@manual_bp.route('/status', methods=['GET'])
def send_status():
    """Retorna el estado actual del sender para el dashboard"""
    try:
        from whatsapp.sender_desktop import get_sender
        sender = get_sender()
        return jsonify(sender.get_status())
    except Exception:
        return jsonify({'logged_in': False, 'sent_today': 0, 'remaining': 50})
