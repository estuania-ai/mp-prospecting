with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    'Próximo envío',
    'Proximas tareas'
)
content = content.replace(
    'Próxima prospección',
    'Proxima actividad'
)

print("Proximas tareas:", 'Proximas tareas' in content)
print("Proxima actividad:", 'Proxima actividad' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")