import sqlite3
conn = sqlite3.connect('data/prospecting.db')
sellers = conn.execute('''
    SELECT id, name, phone, created_at, active
    FROM sellers
    ORDER BY created_at ASC
''').fetchall()
for s in sellers:
    print(f"ID:{s[0]} | {s[1]} | {s[2]} | {s[3]} | activo:{s[4]}")
conn.close()