import sqlite3

conn = sqlite3.connect('data/prospecting.db')

# Actualizar leads de Providencia sin rubro
result = conn.execute("""
    UPDATE leads SET rubro='cafeteria', categoria='Gastronomia y Comida Rapida'
    WHERE (rubro IS NULL OR rubro='') 
    AND (comuna='Providencia' OR name LIKE '%Providencia%' OR name LIKE '%Restobar%' 
         OR name LIKE '%Restaurant%' OR name LIKE '%Bar%' OR name LIKE '%Ramen%'
         OR name LIKE '%Sushi%' OR name LIKE '%Kitchen%' OR name LIKE '%Cocina%')
""")

actualizados = result.rowcount
conn.commit()

# Ver resultado
sin_rubro = conn.execute("""
    SELECT COUNT(*) FROM leads WHERE rubro IS NULL OR rubro=''
""").fetchone()[0]

print(f"Leads actualizados: {actualizados}")
print(f"Leads sin rubro restantes: {sin_rubro}")

if sin_rubro > 0:
    muestra = conn.execute("""
        SELECT id, name, phone, comuna FROM leads 
        WHERE rubro IS NULL OR rubro='' LIMIT 10
    """).fetchall()
    print("Sin rubro:")
    for r in muestra:
        print(f"  ID:{r[0]} | {r[1]} | {r[3]}")

conn.close()
print("OK")