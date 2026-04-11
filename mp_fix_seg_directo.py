with open('templates/dashboard_test3.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar botones exactos actuales
idx = content.find('openStatusModal(${l.id}')
print("Contexto botones:")
print(repr(content[idx:idx+250]))