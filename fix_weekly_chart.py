with open('routes/dashboard.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''    weekly = conn.execute(\'\'\'
        SELECT strftime(\'%W\', sent_at) as week, COUNT(*) as sent
        FROM messages WHERE message_type=\'prospecting\'
        GROUP BY week ORDER BY week DESC LIMIT 8
    \'\'\').fetchall()'''

new = '''    weekly = conn.execute(\'\'\'
        SELECT strftime(\'%W\', sent_at) as week, COUNT(*) as sent
        FROM messages WHERE status=\'sent\'
        GROUP BY week ORDER BY week DESC LIMIT 8
    \'\'\').fetchall()'''

content = content.replace(old, new)

# Tambien corregir total_sent y total_opened
old2 = "    total_sent  = conn.execute(\"SELECT COUNT(*) FROM messages WHERE message_type='prospecting' AND status='sent'\").fetchone()[0]"
new2 = "    total_sent  = conn.execute(\"SELECT COUNT(*) FROM messages WHERE status='sent'\").fetchone()[0]"
content = content.replace(old2, new2)

with open('routes/dashboard.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - dashboard corregido')