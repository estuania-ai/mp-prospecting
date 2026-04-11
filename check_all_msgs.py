import sqlite3
conn = sqlite3.connect('data/prospecting.db')

total = conn.execute("SELECT COUNT(*) FROM messages").fetchone()[0]
print(f'Total mensajes en BD: {total}')

print('\nUltimos 10 mensajes enviados:')
msgs = conn.execute("""
    SELECT m.sent_at, l.name, m.status, m.message_type
    FROM messages m
    LEFT JOIN leads l ON m.lead_id = l.id
    ORDER BY m.sent_at DESC
    LIMIT 10
""").fetchall()
for m in msgs:
    print(f'  {m[0]} | {m[1]} | {m[2]} | {m[3]}')

print('\nLeads con estado enviado:')
enviados = conn.execute("""
    SELECT l.name, ls.updated_at
    FROM lead_status ls
    JOIN leads l ON l.id = ls.lead_id
    WHERE ls.status = 'enviado'
    ORDER BY ls.updated_at DESC
    LIMIT 10
""").fetchall()
for e in enviados:
    print(f'  {e[0]} | {e[1]}')

conn.close()