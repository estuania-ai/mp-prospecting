with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "  if(rubrosChart) rubrosChart.destroy();\n  const ctx = document.getElementById('chartRubros').getContext('2d');"
new = "  if(!document.getElementById('chartRubros')) return;\n  if(rubrosChart) rubrosChart.destroy();\n  const ctx = document.getElementById('chartRubros').getContext('2d');"

if old in content:
    content = content.replace(old, new)
    print("Fix chartRubros OK")
else:
    print("No encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test12.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")