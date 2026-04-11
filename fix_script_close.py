with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Remover el // removed y agregar el cierre correcto
content = content.replace('// removed', '')

# Agregar cierre si no existe
if not content.rstrip().endswith('</html>'):
    content = content.rstrip()
    if not content.endswith('</script>'):
        content += '\n</script>\n'
    content += '\n</body>\n</html>\n'
    print('Cierre agregado')
else:
    print('Ya tiene cierre')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

# Verificar
print('Termina en:', content[-100:])
print('OK')