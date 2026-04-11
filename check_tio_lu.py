import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Buscar todos los mensajes enviados a Pizzeria Tio Lu
msgs = conn.execute("""
    SELECT m.id, m.sent_at, m.status, m.message_type, ls.status as lead_status
    FROM messages m
    LEFT JOIN leads l ON m.lead_id = l.id
    LEFT JOIN lead_status ls ON l.id = ls.lead_id
    WHERE l.name LIKE '%Tio Lu%' OR l.name LIKE '%Tío Lu%'
    ORDER BY m.sent_at ASC
""").fetchall()

print('Mensajes enviados a Pizzeria Tio Lu:')
for m in msgs:
    print(f'  ID:{m[0]} | Fecha:{m[1]} | Estado msg:{m[2]} | Tipo:{m[3]} | Estado lead:{m[4]}')

# Ver estado actual del lead
lead = conn.execute("""
    SELECT l.id, l.phone, ls.status
    FROM leads l
    LEFT JOIN lead_status ls ON l.id = ls.lead_id
    WHERE l.name LIKE '%Tio Lu%' OR l.name LIKE '%Tío Lu%'
""").fetchone()

if lead:
    print(f'Lead actual: id={lead[0]} phone={lead[1]} status={lead[2]}')

conn.close()