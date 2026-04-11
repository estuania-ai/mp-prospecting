import sqlite3
conn = sqlite3.connect('data/prospecting.db')

print("=== Tabla importaciones ===")
try:
    rows = conn.execute("SELECT * FROM importaciones").fetchall()
    print(f"Registros: {len(rows)}")
    for r in rows:
        print(f"  {r}")
except Exception as e:
    print(f"Error: {e}")

print("\n=== Leads no_enviado actuales ===")
rows3 = conn.execute("""
    SELECT COUNT(*) as total FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    WHERE ls.status = 'no_enviado'
""").fetchone()
print(f"  Total no_enviado: {rows3[0]}")
conn.close()