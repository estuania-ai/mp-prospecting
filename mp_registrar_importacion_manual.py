import sqlite3
import json

conn = sqlite3.connect('data/prospecting.db')

# Obtener los IDs de los 72 leads no_enviado
leads = conn.execute("""
    SELECT l.id, l.name, l.rubro FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    WHERE ls.status = 'no_enviado'
    ORDER BY l.id DESC
""").fetchall()

print(f"Leads no_enviado encontrados: {len(leads)}")
for l in leads[:5]:
    print(f"  ID:{l[0]} | {l[1]} | {l[2]}")
print("  ...")

ids = [l[0] for l in leads]

# Registrar como importacion
conn.execute("""
    INSERT INTO importaciones (filename, total_leads, importados, duplicados, lead_ids, created_at)
    VALUES (?, ?, ?, ?, ?, datetime('now','localtime'))
""", ('importacion_previa.xlsx', len(ids), len(ids), 0, json.dumps(ids)))

conn.commit()
print(f"\nImportacion registrada con {len(ids)} leads OK")
conn.close()