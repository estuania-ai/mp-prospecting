import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Ver cuantos leads tienen mensajes enviados pero sin estado 'enviado'
sin_estado = conn.execute("""
    SELECT l.id, l.name, l.phone
    FROM leads l
    LEFT JOIN lead_status ls ON l.id = ls.lead_id
    WHERE ls.lead_id IS NULL OR ls.status = 'no_enviado'
    AND l.phone IN (SELECT phone FROM messages WHERE status = 'sent')
""").fetchall()
print(f"Leads con mensajes enviados pero sin estado correcto: {len(sin_estado)}")

# Marcar como enviado todos los leads que tienen mensajes sent
updated = conn.execute("""
    UPDATE lead_status SET status = 'enviado', updated_at = datetime('now','localtime')
    WHERE lead_id IN (
        SELECT DISTINCT m.lead_id FROM messages m 
        WHERE m.status = 'sent' AND m.lead_id IS NOT NULL
    )
    AND status = 'no_enviado'
""")
print(f"Actualizados a enviado: {updated.rowcount}")

# Ver el total de leads enviados (los 54 que enviaste via whatsapp directo)
# Esos no tienen mensaje en BD pero si tienen estado enviado previo
# Actualizar todos los leads que estaban como 'enviado' antes del cambio a no_enviado
total_enviado = conn.execute("SELECT COUNT(*) FROM lead_status WHERE status='enviado'").fetchone()[0]
total_no_enviado = conn.execute("SELECT COUNT(*) FROM lead_status WHERE status='no_enviado'").fetchone()[0]
print(f"\nEstado actual:")
print(f"  enviado: {total_enviado}")
print(f"  no_enviado: {total_no_enviado}")

conn.commit()
conn.close()
print("OK")