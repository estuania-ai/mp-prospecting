with open('jobs/send_prospecting.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """        WHERE o.phone IS NULL
          AND (ls.status IS NULL OR ls.status NOT IN ('enviado','cerrado','no_interesado','opt_out','telefono_no_existe'))
          AND l.phone IS NOT NULL"""

new = """        WHERE o.phone IS NULL
          AND ls.status IS NULL
          AND l.phone IS NOT NULL
          AND l.phone NOT IN (SELECT DISTINCT phone FROM messages WHERE status = 'sent')"""

content = content.replace(old, new)

with open('jobs/send_prospecting.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - filtro anti-duplicado aplicado')