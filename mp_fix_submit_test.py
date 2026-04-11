with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Eliminar submitStatus comentado
content = content.replace('// submitStatus reemplazado arriba', '')

# Verificar cuantos submitStatus hay
count = content.count('submitStatus()')
print("Referencias a submitStatus():", count)

# Verificar que no haya otro async function submitStatus
count2 = content.count('async function submitStatus')
print("Definiciones de submitStatus:", count2)

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")