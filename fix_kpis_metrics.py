with open('routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    total_leads  = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    total_sent   = conn.execute("SELECT COUNT(*) FROM messages WHERE status='sent'").fetchone()[0]
    total_opened = conn.execute("SELECT COUNT(*) FROM messages WHERE opened_at IS NOT NULL").fetchone()[0]

    by_status = conn.execute(\'\'\'
        SELECT status, COUNT(*) as cnt FROM lead_status GROUP BY status
    \'\'\').fetchall()
    by_status = {r['status']: r['cnt'] for r in by_status}

    # Leads pendientes (no_enviado)
    no_enviado = by_status.get('no_enviado', 0)

    weekly = conn.execute(\'\'\'
        SELECT strftime('%W', sent_at) as week,
               strftime('%Y', sent_at) as year,
               COUNT(*) as sent
        FROM messages WHERE status='sent'
        GROUP BY week, year ORDER BY year DESC, week DESC LIMIT 8
    \'\'\').fetchall()'''

new = '''    total_leads  = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    total_sent   = conn.execute("SELECT COUNT(*) FROM lead_status WHERE status != 'no_enviado'").fetchone()[0]
    total_opened = conn.execute("SELECT COUNT(*) FROM messages WHERE opened_at IS NOT NULL").fetchone()[0]

    by_status = conn.execute(\'\'\'
        SELECT status, COUNT(*) as cnt FROM lead_status GROUP BY status
    \'\'\').fetchall()
    by_status = {r['status']: r['cnt'] for r in by_status}

    no_enviado = by_status.get('no_enviado', 0)

    weekly = conn.execute(\'\'\'
        SELECT strftime('%W', updated_at) as week,
               strftime('%Y', updated_at) as year,
               COUNT(*) as sent
        FROM lead_status
        WHERE status IN ('enviado','interesado','cerrado','quiere_reunion','no_interesado')
        GROUP BY week, year ORDER BY year DESC, week DESC LIMIT 8
    \'\'\').fetchall()'''

content = content.replace(old, new)
print("KPIs fix:", 'lead_status WHERE status' in content)

with open('routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")