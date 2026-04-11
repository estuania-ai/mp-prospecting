with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# El problema es que _loadIntelOld quedo abierta sin cerrar
# Buscar y eliminar ese fragmento roto
idx = content.find('async function _loadIntelOld(){')
if idx > 0:
    print('Funcion rota encontrada en pos:', idx)
    # Eliminarla - encontrar el cierre
    content = content[:idx] + content[idx:].replace('async function _loadIntelOld(){', '// removed', 1)
else:
    print('No se encontro funcion rota')

# Verificar que loadIntel este bien cerrada
idx2 = content.find('function goScraping')
print('goScraping en pos:', idx2)
print('Texto:', content[idx2:idx2+100])

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK')