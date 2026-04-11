import sqlite3

conn = sqlite3.connect('data/prospecting.db')

# 1. Ver cuantos leads tienen telefono 562
total_562 = conn.execute("""
    SELECT COUNT(*) FROM leads WHERE phone LIKE '562%'
""").fetchone()[0]
print(f"Leads con 562: {total_562}")

# 2. Eliminar leads con 562 que no tienen actividad (solo no_enviado)
eliminados = 0
leads_562 = conn.execute("""
    SELECT l.id FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    WHERE l.phone LIKE '562%' AND ls.status = 'no_enviado'
""").fetchall()

for l in leads_562:
    conn.execute('DELETE FROM lead_status WHERE lead_id=?', (l[0],))
    conn.execute('DELETE FROM leads WHERE id=?', (l[0],))
    eliminados += 1

conn.commit()
print(f"Leads 562 eliminados: {eliminados}")

# 3. Ver si quedaron algunos con otro estado
restantes = conn.execute("""
    SELECT l.id, l.name, l.phone, ls.status FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    WHERE l.phone LIKE '562%'
""").fetchall()
print(f"Leads 562 con otro estado (no eliminados): {len(restantes)}")
for r in restantes:
    print(f"  ID:{r[0]} | {r[1]} | {r[2]} | {r[3]}")

conn.close()
print("OK")