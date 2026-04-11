with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

count_async = content.count('async function')
print("Total async functions:", count_async)

# Listar todas
import re
fns = re.findall(r'async function (\w+)', content)
print("Funciones async:", fns)

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)
print("setInterval:", 'setInterval(checkWaStatus' in content)