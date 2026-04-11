import sqlite3
conn = sqlite3.connect('data/prospecting.db')

# Ver leads actuales
print("Estado actual:")
rows = conn.execute("SELECT status, COUNT(*) FROM lead_status GROUP BY status").fetchall()
for r in rows:
    print(f"  {r[0]}: {r[1]}")

# Los 54 leads que ya recibieron mensaje pero quedaron como no_enviado
# los marcamos como enviado con fecha 09/04/2026
sin_registro = conn.execute("""
    SELECT l.id, l.name, l.phone
    FROM leads l
    JOIN lead_status ls ON l.id = ls.lead_id
    WHERE ls.status = 'no_enviado'
    AND l.phone NOT IN (
        SELECT phone FROM messages WHERE status = 'sent'
    )
    LIMIT 50
""").fetchall()

print(f"\nLeads no_enviado sin mensaje registrado: {len(sin_registro)}")

# Preguntar cuantos marcar - por ahora solo marcar los que 
# efectivamente tienen status no_enviado y fueron enviados antes
# Los 49 restantes que mencionaste
confirm = input("\nHay 49 leads en no_enviado que ya recibieron mensaje WhatsApp.\nMarcamos todos como 'enviado' con fecha 09/04/2026? (s/n): ")

if confirm.lower() == 's':
    # Marcar los no_enviado actuales como enviado
    conn.execute("""
        UPDATE lead_status 
        SET status = 'enviado', updated_at = '2026-04-09 15:00:00'
        WHERE status = 'no_enviado'
        AND lead_id NOT IN (
            SELECT DISTINCT lead_id FROM messages WHERE status = 'sent' AND lead_id IS NOT NULL
        )
    """)
    
    # Registrar en messages para trazabilidad
    leads_to_reg = conn.execute("""
        SELECT l.id, l.phone, l.rubro, l.comuna
        FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        WHERE ls.status = 'enviado'
        AND l.phone NOT IN (SELECT phone FROM messages WHERE status='sent')
    """).fetchall()
    
    for lead in leads_to_reg:
        conn.execute("""
            INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
            VALUES (?, ?, 'prospecting', 'sent', '2026-04-09 15:00:00', ?, ?)
        """, (lead[0], lead[1], lead[2], lead[3]))
    
    conn.commit()
    print(f"OK - {len(leads_to_reg)} leads marcados y registrados")
    
    print("\nEstado final:")
    rows2 = conn.execute("SELECT status, COUNT(*) FROM lead_status GROUP BY status").fetchall()
    for r in rows2:
        print(f"  {r[0]}: {r[1]}")
else:
    print("Cancelado")

conn.close()