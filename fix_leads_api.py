with open('routes/leads.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = """        SELECT l.id, l.name, l.phone, l.comuna, l.rubro,
               l.created_at, l.updated_at,
               ls.status, ls.notes,
               m.sent_at, m.opened_at"""

new = """        SELECT l.id, l.name, l.phone, l.comuna, l.rubro, l.categoria,
               l.created_at, l.updated_at,
               ls.status, ls.notes,
               m.sent_at, m.opened_at"""

content = content.replace(old, new)

with open('routes/leads.py', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK - categoria en query")
print("Verificacion:", "l.categoria" in content)