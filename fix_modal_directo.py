with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar donde esta el modal de status
idx = content.find('id="modalStatus"')
print('Modal encontrado en pos:', idx)
print('Texto:', content[idx:idx+200])