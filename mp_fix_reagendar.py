with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar que checkWaStatus existe antes y despues
idx = content.find('function confirmarReagendar()')
print("confirmarReagendar pos:", idx)
print("checkWaStatus antes:", 'function checkWaStatus' in content[:idx])
print("checkWaStatus despues:", 'function checkWaStatus' in content[idx:])

# Solo cambiar function por async function
content = content.replace(
    'function confirmarReagendar(){',
    'async function confirmarReagendar(){'
)

print("async OK:", 'async function confirmarReagendar' in content)
print("checkWaStatus total:", 'function checkWaStatus' in content)
print("loadLeads total:", 'function loadLeads' in content)

with open('templates/dashboard_test7.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")