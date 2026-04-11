with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Corregir campo commune por comuna en el JS del resumen
content = content.replace("c['commune']", "c['comuna']")
content = content.replace('c.commune', 'c.comuna')
content = content.replace("r['commune']", "r['comuna']")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - comunas corregidas')