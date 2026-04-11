"""Crea tabla scraping_jobs para historial"""
import sqlite3
conn = sqlite3.connect('data/prospecting.db')

conn.execute("""
    CREATE TABLE IF NOT EXISTS scraping_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        run_id TEXT,
        tipo TEXT DEFAULT 'search',
        rubro TEXT,
        comuna TEXT,
        maps_url TEXT,
        status TEXT DEFAULT 'running',
        leads_found INTEGER DEFAULT 0,
        leads_inserted INTEGER DEFAULT 0,
        leads_skipped INTEGER DEFAULT 0,
        error TEXT,
        started_at TEXT DEFAULT (datetime('now','localtime')),
        finished_at TEXT
    )
""")
conn.commit()
print("Tabla scraping_jobs OK")

# Registrar el scraping manual que hicimos
conn.execute("""
    INSERT INTO scraping_jobs (run_id, tipo, rubro, comuna, maps_url, status, leads_found, leads_inserted, leads_skipped, finished_at)
    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, datetime('now','localtime'))
""", ('zTiadZvoanGWjVwQq', 'url', 'bazar', 'Las Condes', 'https://maps.google.com/jugueterias', 'succeeded', 78, 70, 8))
conn.commit()
print("Scraping manual registrado OK")
conn.close()
