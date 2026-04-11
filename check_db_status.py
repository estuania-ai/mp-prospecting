import sqlite3
conn = sqlite3.connect('data/prospecting.db')

print("=== lead_status ===")
rows = conn.execute("SELECT status, COUNT(*) FROM lead_status GROUP BY status").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

print("\n=== messages ===")
rows2 = conn.execute("SELECT status, message_type, COUNT(*) FROM messages GROUP BY status, message_type").fetchall()
for r in rows2:
    print(f"  {r[0]} | {r[1]}: {r[2]}")

print("\n=== Muestra lead_status ===")
rows3 = conn.execute("SELECT ls.status, ls.updated_at, l.name FROM lead_status ls JOIN leads l ON l.id=ls.lead_id LIMIT 5").fetchall()
for r in rows3:
    print(f"  {r[0]} | {r[1]} | {r[2]}")

conn.close()