with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """def update_status(lead_id):
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
    return jsonify({'ok': True})"""

new = '''def update_status(lead_id):
    data = request.json
    status = data.get('status')
    notes = data.get('notes')
    optout_motivo = data.get('optout_motivo', '')
    contact_name = data.get('contact_name', '')
    pos_type = data.get('pos_type', 'Point Pro 2')
    email = data.get('email', '')
    if not status:
        return jsonify({'error': 'status required'}), 400
    conn = get_db()
    lead = conn.execute(
        'SELECT id, name, phone, rubro, comuna, categoria FROM leads WHERE id = ?', (lead_id,)
    ).fetchone()
    conn.close()
    if not lead:
        return jsonify({'error': 'lead not found'}), 404
    lead = dict(lead)
    update_lead_status(lead['phone'], status, notes)
    if optout_motivo and status in ('opt_out', 'no_interesado'):
        conn2 = get_db()
        conn2.execute('UPDATE lead_status SET optout_motivo = ? WHERE lead_id = ?', (optout_motivo, lead_id))
        conn2.commit()
        conn2.close()
    if optout_motivo == 'Tiene MP':
        msg = "Que excelente noticia que ya seas parte de Mercado Pago!\\n\\nTe dejo mi contacto: si en el futuro conoces a algun colega o amigo que necesite sumar una maquina a su negocio, feliz de ayudarle con los mejores beneficios!\\n\\nAdemas, cuenta con mi apoyo desde ya. Si alguna vez necesitas orientacion o ayuda con tus equipos o tu cuenta, no dudes en escribirme.\\n\\nMucho exito y excelentes ventas!"
        import threading
        def _send_tienemp(l=lead, lid=lead_id):
            try:
                from whatsapp.sender_desktop import get_sender
                from database import get_db as _db
                sender = get_sender()
                if not sender._is_logged_in:
                    sender.start()
                result = sender.send_message(l['phone'], msg, None)
                c = _db()
                c.execute("INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna) VALUES (?, ?, 'tiene_mp', ?, datetime('now','localtime'), ?, ?)",
                    (lid, l['phone'], 'sent' if result['success'] else 'failed', l.get('rubro',''), l.get('comuna','')))
                c.commit()
                c.close()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error tiene_mp: {e}")
        threading.Thread(target=_send_tienemp, daemon=True).start()
    if status == 'cerrado' and contact_name:
        conn4 = get_db()
        existing = conn4.execute('SELECT id FROM sellers WHERE phone = ?', (lead['phone'],)).fetchone()
        if not existing:
            conn4.execute("INSERT INTO sellers (name, phone, rubro, categoria, pos_type, email, active, closed_at) VALUES (?, ?, ?, ?, ?, ?, 1, datetime('now','localtime'))",
                (contact_name, lead['phone'], lead.get('rubro',''), lead.get('categoria',''), pos_type, email))
            conn4.commit()
        conn4.close()
    return jsonify({'ok': True})'''

if old in content:
    content = content.replace(old, new)
    print("OK - update_status actualizado")
    print("Tiene MP:", 'Tiene MP' in content)
    print("cerrado sellers:", "INSERT INTO sellers" in content)
else:
    print("ERROR - texto no encontrado")

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
