import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Corregir actor al ID correcto
conn.execute("UPDATE config SET value='2Mdma1N6Fd0y3QEjR' WHERE key='apify_actor_id'")
conn.commit()

# Verificar
rows = conn.execute("SELECT key, value FROM config WHERE key LIKE '%apify%'").fetchall()
for r in rows:
    print(f"{r[0]}: {r[1]}")
conn.close()
print("OK actor corregido")