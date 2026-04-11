with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    # Si se marca como cerrado -> agregar automaticamente a Sellers
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

new = '''    # Si se marca como cerrado -> agregar automaticamente a Sellers con datos completos
    if status == 'cerrado':
        try:
            contact_name = data.get('contact_name', '')
            pos_type     = data.get('pos_type', 'Point Pro 2')
            email        = data.get('email', '')
            conn2 = get_db()
            existing = conn2.execute('SELECT id FROM sellers WHERE phone = ?', (lead['phone'],)).fetchone()
            if not existing:
                conn2.execute("""
                    INSERT INTO sellers (name, contact_name, phone, pos_type, comuna, email, notes, active, created_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 1, datetime('now','localtime'))
                """, (
                    lead['name'],
                    contact_name,
                    lead['phone'],
                    pos_type,
                    lead['comuna'] or '',
                    email,
                    f"Adquirido via prospeccion - Rubro: {lead['rubro']}. {notes or ''}"
                ))
            else:
                conn2.execute("""
                    UPDATE sellers SET contact_name=?, pos_type=?, email=?, notes=?
                    WHERE phone=?
                """, (contact_name, pos_type, email,
                      f"Actualizado - Rubro: {lead['rubro']}. {notes or ''}",
                      lead['phone']))
            conn2.commit()
            conn2.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error agregando seller: {e}")

    return jsonify({'ok': True, 'auto_seller': status == 'cerrado'})'''

content = content.replace(old, new)

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - leads.py actualizado')