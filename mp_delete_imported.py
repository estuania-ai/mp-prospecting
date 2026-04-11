import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Ver importaciones registradas
imps = conn.execute("SELECT id, filename, importados, created_at, lead_ids FROM importaciones ORDER BY created_at DESC").fetchall()
print("Importaciones registradas:")
for i in imps:
    print(f"  ID:{i[0]} | {i[1]} | {i[2]} leads | {i[3]}")

if not imps:
    print("No hay importaciones registradas")
    # Eliminar directamente los ultimos 72 leads no_enviado
    leads = conn.execute("""
        SELECT l.id FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        WHERE ls.status = 'no_enviado'
        ORDER BY l.id DESC LIMIT 72
    """).fetchall()
    print(f"\nEliminando ultimos {len(leads)} leads no_enviado...")
    for l in leads:
        conn.execute('DELETE FROM lead_status WHERE lead_id=?', (l[0],))
        conn.execute('DELETE FROM leads WHERE id=?', (l[0],))
    conn.commit()
    print(f"OK - {len(leads)} leads eliminados")
else:
    # Eliminar por importacion
    imp = imps[0]
    import json
    ids = json.loads(imp[4] or '[]')
    print(f"\nEliminando importacion ID:{imp[0]} - {len(ids)} leads...")
    for lid in ids:
        conn.execute('DELETE FROM lead_status WHERE lead_id=?', (lid,))
        conn.execute('DELETE FROM leads WHERE id=?', (lid,))
    conn.execute('DELETE FROM importaciones WHERE id=?', (imp[0],))
    conn.commit()
    print(f"OK - {len(ids)} leads eliminados")

conn.close()