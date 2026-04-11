import sqlite3
from datetime import datetime

conn = sqlite3.connect('data/prospecting.db')

# Verificar que la query de seguimiento encuentra leads
rows = conn.execute('''
    SELECT l.id, l.name, l.phone, l.comuna, l.rubro,
           m.sent_at,
           CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas_desde_envio
    FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    JOIN messages m ON l.id = m.lead_id
    LEFT JOIN opt_out o ON l.phone = o.phone
    WHERE ls.status = 'enviado'
      AND m.status = 'sent'
      AND m.message_type IN ('prospecting', 'manual')
      AND o.phone IS NULL
      AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= 24
      AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) < 25
      AND l.phone NOT IN (
          SELECT DISTINCT phone FROM messages
          WHERE message_type = 'seguimiento_24h' AND status = 'sent'
      )
    GROUP BY l.id
''').fetchall()

print(f"Leads para seguimiento 24h: {len(rows)}")
for r in rows:
    print(f"  {r[1]} | {r[2]} | {r[6]}h")

# Ver todos los mensajes del lead 1
print("\nMensajes de lead ID:1:")
msgs = conn.execute("SELECT message_type, status, sent_at FROM messages WHERE lead_id = 1").fetchall()
for m in msgs:
    print(f"  {m[0]} | {m[1]} | {m[2]}")

conn.close()