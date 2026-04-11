with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = "    status = data.get('status')\n    notes = data.get('notes')"
new = "    status = data.get('status')\n    notes = data.get('notes')\n    optout_motivo = data.get('optout_motivo', '')"

content = content.replace(old, new)

old2 = "    update_lead_status(lead['phone'], status, notes)"
new2 = """    update_lead_status(lead['phone'], status, notes)

    # Guardar motivo optout si aplica
    if optout_motivo and status in ('opt_out', 'no_interesado'):
        conn2 = get_db()
        conn2.execute(
            'UPDATE lead_status SET optout_motivo = ? WHERE lead_id = ?',
            (optout_motivo, lead_id)
        )
        conn2.commit()
        conn2.close()"""

content = content.replace(old2, new2)

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK leads.py - optout_motivo guardado")