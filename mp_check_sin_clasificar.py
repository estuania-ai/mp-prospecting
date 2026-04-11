import sqlite3

conn = sqlite3.connect('data/prospecting.db')

sin_comuna = conn.execute("""
    SELECT id, name, phone, rubro, comuna FROM leads 
    WHERE comuna IS NULL OR comuna='' OR comuna='Sin clasificar'
    ORDER BY id DESC
""").fetchall()

print(f"Leads sin comuna: {len(sin_comuna)}")
for r in sin_comuna:
    print(f"  ID:{r[0]} | {r[1][:40]} | {r[2]} | {r[3]} | '{r[4]}'")

conn.close()