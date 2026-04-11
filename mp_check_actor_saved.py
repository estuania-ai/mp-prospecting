import sqlite3
conn = sqlite3.connect('data/prospecting.db')
rows = conn.execute("SELECT key, value FROM config WHERE key LIKE '%apify%'").fetchall()
for r in rows:
    print(f"{r[0]}: {r[1]}")
conn.close()