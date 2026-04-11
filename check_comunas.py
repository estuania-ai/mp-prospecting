import sqlite3
conn = sqlite3.connect('data/prospecting.db')
rows = conn.execute('SELECT comuna, COUNT(*) as total FROM leads GROUP BY comuna').fetchall()
for r in rows:
    print(r)
conn.close()