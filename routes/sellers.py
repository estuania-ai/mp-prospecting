"""Rutas Flask: Sellers con etapas de fidelizacion"""
from flask import Blueprint, request, jsonify
from database import get_db

sellers_bp = Blueprint('sellers', __name__)

@sellers_bp.route('/', methods=['GET'])
def get_sellers():
    conn = get_db()
    rows = conn.execute('''
        SELECT s.*,
            CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) as dias_desde_cierre,
            (SELECT COUNT(*) FROM messages m WHERE m.phone = s.phone AND m.message_type = 'fidelizacion' AND m.status = 'sent') as total_fidelizacion_enviados,
            (SELECT MAX(m.sent_at) FROM messages m WHERE m.phone = s.phone AND m.message_type = 'fidelizacion') as ultimo_fidelizacion
        FROM sellers s
        WHERE s.active = 1
        ORDER BY s.created_at DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])

@sellers_bp.route('/', methods=['POST'])
def add_seller():
    data = request.json or {}
    if not data.get('name') or not data.get('phone'):
        return jsonify({'error': 'name y phone requeridos'}), 400
    conn = get_db()
    conn.execute('''
        INSERT INTO sellers (name, contact_name, phone, pos_type, comuna, rubro, categoria, email, notes, active, created_at, closed_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1, datetime('now','localtime'), datetime('now','localtime'))
    ''', (
        data.get('name'), data.get('contact_name',''),
        data.get('phone'), data.get('pos_type','Point Pro 2'),
        data.get('comuna',''), data.get('rubro',''),
        data.get('categoria',''), data.get('email',''),
        data.get('notes','')
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@sellers_bp.route('/<int:seller_id>', methods=['DELETE'])
def delete_seller(seller_id):
    conn = get_db()
    conn.execute('UPDATE sellers SET active = 0 WHERE id = ?', (seller_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})

@sellers_bp.route('/broadcast', methods=['POST'])
def broadcast_sellers():
    """Envia mensaje masivo a todos los sellers activos"""
    data = request.json or {}
    mensaje = data.get('mensaje', '').strip()
    seller_ids = data.get('seller_ids', [])

    if not mensaje:
        return jsonify({'error': 'Mensaje requerido'}), 400

    conn = get_db()
    if seller_ids:
        placeholders = ','.join('?' * len(seller_ids))
        sellers = conn.execute(f'''
            SELECT s.id, s.name, s.phone FROM sellers s
            LEFT JOIN opt_out o ON s.phone = o.phone
            WHERE s.id IN ({placeholders}) AND s.active = 1 AND o.phone IS NULL
        ''', seller_ids).fetchall()
    else:
        sellers = conn.execute('''
            SELECT s.id, s.name, s.phone FROM sellers s
            LEFT JOIN opt_out o ON s.phone = o.phone
            WHERE s.active = 1 AND o.phone IS NULL
        ''').fetchall()
    conn.close()

    if not sellers:
        return jsonify({'error': 'Sin sellers disponibles'}), 400

    import threading
    def _send():
        from whatsapp.sender_desktop import get_sender
        from database import get_db as _db
        sender = get_sender()
        if not sender._is_logged_in:
            sender.start()
        for s in sellers:
            sd = dict(s)
            result = sender.send_message(sd['phone'], mensaje, None)
            conn2 = _db()
            conn2.execute('''
                INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
                VALUES (?, ?, 'broadcast', ?, datetime('now','localtime'), 'broadcast', '')
            ''', (sd['id'], sd['phone'], 'sent' if result['success'] else 'failed'))
            conn2.execute("UPDATE sellers SET last_msg_at = datetime('now','localtime') WHERE id = ?", (sd['id'],))
            conn2.commit()
            conn2.close()

    t = threading.Thread(target=_send)
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'message': f'Enviando a {len(sellers)} sellers en segundo plano', 'total': len(sellers)})

@sellers_bp.route('/etapas', methods=['GET'])
def get_etapas():
    """Retorna el estado de etapas de fidelizacion por seller"""
    from fidelizacion_config import ETAPAS
    conn = get_db()
    sellers = conn.execute('''
        SELECT s.id, s.name, s.phone, s.closed_at, s.rubro, s.categoria,
            CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) as dias
        FROM sellers s WHERE s.active = 1 AND s.closed_at IS NOT NULL
    ''').fetchall()

    result = []
    for s in sellers:
        sd = dict(s)
        etapas_info = []
        for dias, key, nombre in ETAPAS:
            enviado = conn.execute('''
                SELECT COUNT(*) FROM messages
                WHERE phone = ? AND message_type = 'fidelizacion'
                AND rubro = ? AND status = 'sent'
            ''', (sd['phone'], f'etapa_{dias}')).fetchone()[0]
            pendiente = sd['dias'] >= dias and not enviado
            etapas_info.append({
                'dias': dias, 'key': key, 'nombre': nombre,
                'enviado': bool(enviado), 'pendiente': pendiente
            })
        sd['etapas'] = etapas_info
        sd['total_enviados'] = sum(1 for e in etapas_info if e['enviado'])
        sd['ciclo_completo'] = all(e['enviado'] for e in etapas_info)
        result.append(sd)

    conn.close()
    return jsonify(result)
