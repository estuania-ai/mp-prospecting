with open('jobs/send_seguimiento.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """          AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= ?
          AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) < ?
          AND l.phone NOT IN (
              SELECT DISTINCT phone FROM messages
              WHERE message_type = 'seguimiento_{tipo}'
              AND status = 'sent'
          )
        GROUP BY l.id
        ORDER BY m.sent_at ASC
    ''', (horas, horas + 1)).fetchall()"""

new = """          AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= ?
          AND l.phone NOT IN (
              SELECT DISTINCT phone FROM messages
              WHERE message_type = 'seguimiento_{tipo}'
              AND status = 'sent'
          )
        GROUP BY l.id
        ORDER BY m.sent_at ASC
    ''', (horas,)).fetchall()"""

if old in content:
    content = content.replace(old, new)
    print("Query corregida OK")
else:
    print("No encontrado exacto - reescribiendo archivo completo")

with open('jobs/send_seguimiento.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")