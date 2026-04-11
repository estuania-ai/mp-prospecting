import sqlite3
conn = sqlite3.connect('data/prospecting.db')

print("=== Leads recientes ===")
leads = conn.execute("""
    SELECT l.id, l.name, l.phone, l.rubro, l.comuna, ls.status
    FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    ORDER BY l.id DESC LIMIT 10
""").fetchall()
for l in leads:
    print(f"  ID:{l[0]} | {l[1]} | {l[2]} | {l[3]} | {l[4]} | {l[5]}")

print(f"\nTotal leads: {conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]}")
conn.close()