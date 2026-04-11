import sqlite3
conn = sqlite3.connect('data/prospecting.db')
conn.execute('DELETE FROM sellers WHERE active = 0')
conn.commit()
total = conn.execute('SELECT COUNT(*) FROM sellers').fetchone()[0]
print(f'OK - sellers activos restantes: {total}')
rows = conn.execute('SELECT id, name, phone FROM sellers ORDER BY id').fetchall()
for r in rows:
    print(f'  ID:{r[0]} | {r[1]} | {r[2]}')
conn.close()