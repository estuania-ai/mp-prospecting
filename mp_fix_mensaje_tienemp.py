with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar envio automatico cuando motivo es 'Tiene MP'
old = """    # Guardar motivo optout si aplica
    if optout_motivo and status in ('opt_out', 'no_interesado'):
        conn2 = get_db()
        conn2.execute(
            'UPDATE lead_status SET optout_motivo = ? WHERE lead_id = ?',
            (optout_motivo, lead_id)
        )
        conn2.commit()
        conn2.close()"""

new = """    # Guardar motivo optout si aplica
    if optout_motivo and status in ('opt_out', 'no_interesado'):
        conn2 = get_db()
        conn2.execute(
            'UPDATE lead_status SET optout_motivo = ? WHERE lead_id = ?',
            (optout_motivo, lead_id)
        )
        conn2.commit()
        conn2.close()

    # Envio automatico si motivo es Tiene MP
    if optout_motivo == 'Tiene MP':
        msg = (
            "Que excelente noticia que ya seas parte de Mercado Pago!\\n\\n"
            "Te dejo mi contacto: si en el futuro conoces a algun colega o amigo que necesite "
            "sumar una maquina a su negocio, feliz de ayudarle con los mejores beneficios!\\n\\n"
            "Ademas, cuenta con mi apoyo desde ya. Si alguna vez necesitas orientacion o ayuda "
            "con tus equipos o tu cuenta, no dudes en escribirme.\\n\\n"
            "Mucho exito y excelentes ventas!"
        )
        import threading
        lead_data = lead.copy() if isinstance(lead, dict) else dict(lead)
        def _send_tienemp():
            try:
                from whatsapp.sender_desktop import get_sender
                from database import get_db as _db
                sender = get_sender()
                if not sender._is_logged_in:
                    sender.start()
                result = sender.send_message(lead_data['phone'], msg, None)
                conn3 = _db()
                conn3.execute(
                    "INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna) VALUES (?, ?, 'tiene_mp', ?, datetime('now','localtime'), ?, ?)",
                    (lead_id, lead_data['phone'], 'sent' if result['success'] else 'failed',
                     lead_data.get('rubro',''), lead_data.get('comuna',''))
                )
                conn3.commit()
                conn3.close()
            except Exception as e:
                import logging
                logging.getLogger(__name__).error(f"Error enviando mensaje tiene_mp: {e}")
        t = threading.Thread(target=_send_tienemp)
        t.daemon = True
        t.start()"""

if old in content:
    content = content.replace(old, new)
    print("OK mensaje Tiene MP agregado")
else:
    print("Texto no encontrado")
    idx = content.find('optout_motivo')
    print("Contexto:", content[idx:idx+200])

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")