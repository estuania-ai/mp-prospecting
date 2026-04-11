import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Fecha de cierre real de cada seller (ajusta segun cuando los cerraste)
sellers_fechas = [
    (1,  '2026-04-02'),  # EMPORIO VILLA LAS CASAS
    (2,  '2026-04-05'),  # Carniceria Reyes de la Marina
    (3,  '2026-04-05'),  # Madhu
    (6,  '2026-04-05'),  # Mani fruits y nuts
    (7,  '2026-04-05'),  # La Casona
    (8,  '2026-04-05'),  # Alamcen Pitufo
    (9,  '2026-04-05'),  # Botilleria Don Coty
    (10, '2026-04-05'),  # Bonna Pizza
    (13, '2026-04-05'),  # TEST Prospecto
]

for seller_id, fecha in sellers_fechas:
    conn.execute(
        "UPDATE sellers SET closed_at = ? WHERE id = ?",
        (fecha + ' 12:00:00', seller_id)
    )

conn.commit()
verificar = conn.execute('SELECT id, name, closed_at FROM sellers ORDER BY id').fetchall()
for r in verificar:
    print(f'ID:{r[0]} | {r[1]} | cierre: {r[2]}')
conn.close()
print('OK - fechas de cierre actualizadas')