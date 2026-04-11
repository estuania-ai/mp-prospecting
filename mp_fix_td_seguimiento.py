with open('templates/dashboard_test3.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el td de estado para insertar seguimiento despues
idx = content.find("badge(l.status||'enviado')")
print("Contexto td estado:")
print(repr(content[idx:idx+200]))