with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar exactamente los botones actuales en la tabla
idx = content.find('openStatusModal(${l.id}')
print("openStatusModal pos:", idx)
print("Contexto:", content[idx:idx+200])