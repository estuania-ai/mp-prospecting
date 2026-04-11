import sqlite3

conn = sqlite3.connect('data/prospecting.db')

# Agregar registro de restaurantes Providencia
conn.execute("""
    INSERT INTO scraping_jobs (run_id, tipo, rubro, maps_url, status, leads_found, leads_inserted, leads_skipped, started_at, finished_at)
    VALUES ('EaUdF89LzGxuSR8ae', 'url', 'cafeteria', 'Google Maps - Restaurantes Providencia', 'succeeded', 100, 85, 15, '2026-04-11 15:32', '2026-04-11 15:33')
""")

conn.commit()

# Ver resultado final
rows = conn.execute("""
    SELECT id, rubro, maps_url, leads_found, leads_inserted, started_at, status 
    FROM scraping_jobs ORDER BY started_at DESC
""").fetchall()

print("Historial final:")
for r in rows:
    print(f"  ID:{r[0]} | {r[5]} | rubro:{r[1]} | encontrados:{r[3]} | insertados:{r[4]} | {r[6]}")

conn.close()
print("OK")