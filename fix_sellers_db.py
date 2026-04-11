"""Migra la tabla sellers para soportar fidelizacion por etapas"""
import sqlite3

conn = sqlite3.connect('data/prospecting.db')

# Agregar columnas que faltan si no existen
cols_to_add = [
    ('closed_at',    'TEXT'),
    ('categoria',    'TEXT'),
    ('rubro',        'TEXT'),
    ('contact_name', 'TEXT'),
    ('pos_type',     'TEXT DEFAULT "Point Pro 2"'),
    ('email',        'TEXT'),
]

existing = [row[1] for row in conn.execute('PRAGMA table_info(sellers)').fetchall()]
print('Columnas actuales:', existing)

for col, tipo in cols_to_add:
    if col not in existing:
        conn.execute(f'ALTER TABLE sellers ADD COLUMN {col} {tipo}')
        print(f'Columna agregada: {col}')
    else:
        print(f'Ya existe: {col}')

# Poblar closed_at desde lead_status donde status=cerrado
conn.execute('''
    UPDATE sellers SET closed_at = (
        SELECT ls.updated_at FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.phone = sellers.phone AND ls.status = 'cerrado'
        ORDER BY ls.updated_at DESC LIMIT 1
    )
    WHERE closed_at IS NULL
''')

# Poblar categoria desde leads
conn.execute('''
    UPDATE sellers SET
        rubro = (SELECT l.rubro FROM leads l WHERE l.phone = sellers.phone LIMIT 1),
        categoria = (SELECT l.rubro FROM leads l WHERE l.phone = sellers.phone LIMIT 1)
    WHERE rubro IS NULL
''')

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM sellers').fetchone()[0]
con_fecha = conn.execute('SELECT COUNT(*) FROM sellers WHERE closed_at IS NOT NULL').fetchone()[0]
print(f'Total sellers: {total} | Con fecha cierre: {con_fecha}')

conn.close()
print('OK - BD sellers actualizada')
