import sqlite3
import re

conn = sqlite3.connect('data/prospecting.db')

leads = conn.execute("""
    SELECT l.id, l.phone, ls.status
    FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
""").fetchall()

print(f"Total leads: {len(leads)}")

eliminados = 0
conservados_con_actividad = 0

for l in leads:
    lead_id, phone, status = l[0], l[1] or '', l[2]
    digits = re.sub(r'\D', '', phone)
    
    # Solo valido: 569 + 8 digitos = 11 digitos total
    if not re.match(r'^569\d{8}$', digits):
        if status == 'no_enviado':
            conn.execute('DELETE FROM lead_status WHERE lead_id=?', (lead_id,))
            conn.execute('DELETE FROM leads WHERE id=?', (lead_id,))
            eliminados += 1
        else:
            print(f"  Conservado (actividad): ID:{lead_id} | {phone} | {status}")
            conservados_con_actividad += 1

conn.commit()

total = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
print(f"\nEliminados: {eliminados}")
print(f"Conservados con actividad: {conservados_con_actividad}")
print(f"Total leads restantes: {total}")

# Verificar que no quedan invalidos
todos = conn.execute("SELECT id, phone FROM leads").fetchall()
invalidos_restantes = [(r[0], r[1]) for r in todos if not re.match(r'^569\d{8}$', re.sub(r'\D','',r[1] or ''))]
print(f"Invalidos restantes: {len(invalidos_restantes)}")
for r in invalidos_restantes[:5]:
    print(f"  ID:{r[0]} | {r[1]}")

conn.close()
print("OK")