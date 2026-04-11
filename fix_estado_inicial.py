import sqlite3

# Actualizar send_prospecting.py - solo enviar a no_enviado
with open('jobs/send_prospecting.py', 'r', encoding='utf-8') as f:
    sp = f.read()

sp = sp.replace(
    "AND ls.status IS NULL\n          AND l.phone IS NOT NULL\n          AND l.phone NOT IN (SELECT DISTINCT phone FROM messages WHERE status = 'sent')",
    "AND ls.status = 'no_enviado'\n          AND l.phone IS NOT NULL"
)
sp = sp.replace(
    "lead_status = 'enviado' if success else ('telefono_no_existe' if error == 'phone_not_exists' else 'enviado')",
    "lead_status = 'enviado' if success else ('telefono_no_existe' if error == 'phone_not_exists' else 'no_enviado')"
)

with open('jobs/send_prospecting.py', 'w', encoding='utf-8') as f:
    f.write(sp)
print('OK send_prospecting.py')

# Marcar leads ya enviados como enviado y el resto como no_enviado
conn = sqlite3.connect('data/prospecting.db')

# Leads que ya tienen mensajes enviados -> estado enviado
conn.execute("""
    UPDATE lead_status SET status = 'enviado'
    WHERE lead_id IN (
        SELECT DISTINCT lead_id FROM messages WHERE status = 'sent' AND lead_id IS NOT NULL
    )
""")

# Leads sin estado -> no_enviado
sin_estado = conn.execute("""
    SELECT l.id FROM leads l
    LEFT JOIN lead_status ls ON l.id = ls.lead_id
    WHERE ls.lead_id IS NULL
""").fetchall()

for row in sin_estado:
    conn.execute(
        "INSERT OR IGNORE INTO lead_status (lead_id, status, updated_at) VALUES (?, 'no_enviado', datetime('now','localtime'))",
        (row[0],)
    )

conn.commit()
print(f'OK - {len(sin_estado)} leads marcados como no_enviado')

# Verificar
stats = conn.execute("SELECT status, COUNT(*) FROM lead_status GROUP BY status").fetchall()
for s in stats:
    print(f'  {s[0]}: {s[1]} leads')
conn.close()