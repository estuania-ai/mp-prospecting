import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Ver mensajes enviados sin campana
msgs = conn.execute("""
    SELECT COUNT(*) as total, MIN(sent_at) as inicio, MAX(sent_at) as fin
    FROM messages WHERE status='sent'
""").fetchone()

print('Mensajes enviados:', msgs[0])
print('Desde:', msgs[1])
print('Hasta:', msgs[2])

# Crear campana retroactiva
conn.execute("""
    INSERT INTO campaigns (name, total_sent, sent_at, status)
    VALUES (?, ?, ?, 'completed')
""", (
    f"Prospeccion manual 09/04/2026 - Pizzerias Puente Alto",
    msgs[0],
    msgs[2]
))
conn.commit()
conn.close()
print('OK - campana registrada')