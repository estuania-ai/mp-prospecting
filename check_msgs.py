import sqlite3
conn = sqlite3.connect('data/prospecting.db')
msgs = conn.execute('''
    SELECT sent_at, status, COUNT(*) as total
    FROM messages
    WHERE date(sent_at) = date('now','localtime')
    GROUP BY sent_at, status
    ORDER BY sent_at DESC
''').fetchall()
if msgs:
    for m in msgs:
        print(m)
else:
    print('Sin mensajes enviados hoy')
conn.close()