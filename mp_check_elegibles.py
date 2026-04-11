import sqlite3
conn = sqlite3.connect('data/prospecting.db')

rows = conn.execute("""
    SELECT l.id, l.name, ls.status, m.message_type,
           CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
    FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    JOIN messages m ON l.id = m.lead_id
    WHERE m.status = 'sent'
    AND m.message_type IN ('prospecting','manual')
    GROUP BY l.id
    ORDER BY horas DESC
""").fetchall()

print('ID | Nombre | Estado | Horas | Elegible seguimiento')
print('-'*65)
for r in rows:
    elegible = 'SI' if r[2]=='enviado' else 'NO - estado: '+r[2]
    print(f"  {r[0]} | {r[1][:20]:<20} | {r[2]:<15} | {r[4]}h | {elegible}")

conn.close()