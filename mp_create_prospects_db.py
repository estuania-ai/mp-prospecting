import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Tabla prospects - prospectos interesados con info detallada
conn.execute("""
    CREATE TABLE IF NOT EXISTS prospects (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lead_id INTEGER REFERENCES leads(id),
        name TEXT NOT NULL,
        phone TEXT NOT NULL,
        negocio TEXT,
        rubro TEXT,
        categoria TEXT,
        comuna TEXT,
        competencia TEXT,
        procedencia TEXT DEFAULT 'Online',
        notas TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime')),
        updated_at TEXT DEFAULT (datetime('now','localtime'))
    )
""")

# Tabla tasks - agenda de tareas por prospecto
conn.execute("""
    CREATE TABLE IF NOT EXISTS tasks (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        prospect_id INTEGER REFERENCES prospects(id),
        lead_id INTEGER REFERENCES leads(id),
        tipo TEXT NOT NULL,
        descripcion TEXT,
        fecha TEXT NOT NULL,
        hora TEXT,
        completada INTEGER DEFAULT 0,
        completada_at TEXT,
        nota_reagenda TEXT,
        created_at TEXT DEFAULT (datetime('now','localtime'))
    )
""")

conn.commit()

# Verificar
tables = conn.execute("SELECT name FROM sqlite_master WHERE type='table'").fetchall()
print("Tablas en BD:")
for t in tables:
    print(f"  {t[0]}")

# Agregar columna procedencia a leads si no existe
cols = [r[1] for r in conn.execute('PRAGMA table_info(leads)').fetchall()]
if 'procedencia' not in cols:
    conn.execute('ALTER TABLE leads ADD COLUMN procedencia TEXT DEFAULT "Online"')
    conn.commit()
    print("Columna procedencia agregada a leads")

conn.close()
print("OK BD actualizada")