import sqlite3
conn = sqlite3.connect('data/prospecting.db')

conn.execute("""
    CREATE TABLE IF NOT EXISTS importaciones (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        filename TEXT NOT NULL,
        total_leads INTEGER DEFAULT 0,
        importados INTEGER DEFAULT 0,
        duplicados INTEGER DEFAULT 0,
        lead_ids TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
""")
conn.commit()
print("Tabla importaciones OK")
conn.close()
