with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el modal de status
idx = content.find('modalStatus')
print("Modal status pos:", idx)
print("Contenido:", content[idx:idx+800])