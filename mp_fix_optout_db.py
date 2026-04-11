import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Agregar columna optout_motivo a lead_status si no existe
cols = [r[1] for r in conn.execute('PRAGMA table_info(lead_status)').fetchall()]
if 'optout_motivo' not in cols:
    conn.execute('ALTER TABLE lead_status ADD COLUMN optout_motivo TEXT')
    conn.commit()
    print("Columna optout_motivo agregada")
else:
    print("Ya existe")

conn.close()
print("OK BD actualizada")