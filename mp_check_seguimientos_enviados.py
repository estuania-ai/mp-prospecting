import sqlite3
conn = sqlite3.connect('data/prospecting.db')
rows = conn.execute("""
    SELECT l.name, m.message_type, m.status, m.sent_at
    FROM messages m
    JOIN leads l ON l.id = m.lead_id
    WHERE m.message_type IN ('seguimiento_24h','seguimiento_72h')
    ORDER BY m.sent_at DESC
""").fetchall()
print(f"Seguimientos registrados: {len(rows)}")
for r in rows:
    print(f"  {r[0]} | {r[1]} | {r[2]} | {r[3]}")
conn.close()