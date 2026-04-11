import sqlite3
conn = sqlite3.connect('data/prospecting.db')

print("=== Historial scraping ===")
rows = conn.execute("""
    SELECT id, run_id, tipo, rubro, maps_url, leads_found, leads_inserted, started_at, status
    FROM scraping_jobs ORDER BY started_at DESC
""").fetchall()
for r in rows:
    print(f"  ID:{r[0]} | {r[7]} | tipo:{r[2]} | rubro:{r[3]} | insertados:{r[6]}")

conn.close()