import sqlite3
conn = sqlite3.connect('data/prospecting.db')

print("=== Weekly data ===")
rows = conn.execute("""
    SELECT strftime('%W', updated_at) as week,
           strftime('%Y', updated_at) as year,
           COUNT(*) as sent
    FROM lead_status
    WHERE status IN ('enviado','interesado','cerrado','quiere_reunion','no_interesado')
    GROUP BY week, year ORDER BY year DESC, week DESC LIMIT 8
""").fetchall()
for r in rows:
    print(f"  Sem {r[0]} {r[1]}: {r[2]} registros")

print("\n=== By status ===")
rows2 = conn.execute("SELECT status, COUNT(*) FROM lead_status GROUP BY status").fetchall()
for r in rows2:
    print(f"  {r[0]}: {r[1]}")

print("\n=== Top comunas ===")
rows3 = conn.execute("""
    SELECT l.comuna, COUNT(*) as total
    FROM leads l
    WHERE l.comuna IS NOT NULL AND l.comuna != ''
    GROUP BY l.comuna ORDER BY total DESC LIMIT 5
""").fetchall()
for r in rows3:
    print(f"  {r[0]}: {r[1]}")

conn.close()