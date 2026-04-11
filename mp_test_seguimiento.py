import sqlite3
from datetime import datetime, timedelta

conn = sqlite3.connect('data/prospecting.db')

# Ver leads con estado enviado
leads = conn.execute("""
    SELECT l.id, l.name, l.phone, ls.status, m.sent_at,
           CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
    FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    LEFT JOIN messages m ON l.id = m.lead_id AND m.status = 'sent'
    WHERE ls.status = 'enviado'
    LIMIT 5
""").fetchall()

print("=== Leads enviados ===")
for l in leads:
    print(f"  ID:{l[0]} | {l[1]} | horas desde envio: {l[5]}")

# Simular que el primer lead fue enviado hace 25 horas
if leads:
    lead = leads[0]
    fecha_simulada = (datetime.now() - timedelta(hours=25)).strftime('%Y-%m-%d %H:%M:%S')
    conn.execute("UPDATE messages SET sent_at = ? WHERE lead_id = ? AND status = 'sent'",
                 (fecha_simulada, lead[0]))
    conn.commit()
    print(f"\nSimulado: {lead[1]} enviado hace 25h (fecha: {fecha_simulada})")
    print("Ahora ejecuta: python -c \"from jobs.send_seguimiento import run_seguimiento; run_seguimiento()\"")

conn.close()