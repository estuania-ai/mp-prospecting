with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Eliminar el submitStatus comentado
content = content.replace('// submitStatus reemplazado arriba', '')

# Verificar onStatusChange existe
print("onStatusChange existe:", 'function onStatusChange' in content)
print("camposOptout existe en HTML:", 'id="camposOptout"' in content)
print("camposCerrado existe en HTML:", 'id="camposCerrado"' in content)

# Verificar que openStatusModal resetea los campos
idx = content.find('function openStatusModal')
print("\nopenStatusModal:", content[idx:idx+300])

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("\nOK")