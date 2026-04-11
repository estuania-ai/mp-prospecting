with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''@leads_bp.route('/<int:lead_id>/status', methods=['PUT'])
def update_status(lead_id):
    data = request.json
    status = data.get('status')
    notes = data.get('notes')
    if not status:
        return jsonify({'error': 'status required'}), 400
    conn = get_db()
    lead = conn.execute('SELECT phone FROM leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()
    if not lead:
        return jsonify({'error': 'lead not found'}), 404
    update_lead_status(lead['phone'], status, notes)
    return jsonify({'ok': True})'''

new = '''@leads_bp.route('/<int:lead_id>/status', methods=['PUT'])
def update_status(lead_id):
    data = request.json
    status = data.get('status')
    notes = data.get('notes')
    if not status:
        return jsonify({'error': 'status required'}), 400
    conn = get_db()
    lead = conn.execute('SELECT id, name, phone, comuna, rubro FROM leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()
    if not lead:
        return jsonify({'error': 'lead not found'}), 404
    update_lead_status(lead['phone'], status, notes)

    # Si se marca como cerrado -> agregar automaticamente a Sellers
    if status == 'cerrado':
        try:
            conn2 = get_db()
            existing = conn2.execute('SELECT id FROM sellers WHERE phone = ?', (lead['phone'],)).fetchone()
            if not existing:
                conn2.execute("""
                    INSERT INTO sellers (name, phone, comuna, notes, active, created_at)
                    VALUES (?, ?, ?, ?, 1, datetime('now','localtime'))
                """, (
                    lead['name'],
                    lead['phone'],
                    lead['comuna'] or '',
                    f"Adquirido via prospeccion - Rubro: {lead['rubro']}. {notes or ''}"
                ))
                conn2.commit()
            conn2.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error agregando seller: {e}")

    return jsonify({'ok': True, 'auto_seller': status == 'cerrado'})'''

content = content.replace(old, new)

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - cierre auto a sellers')