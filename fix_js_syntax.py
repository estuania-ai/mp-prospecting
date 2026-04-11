with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el bloque script y verificar que cierres bien
script_start = content.rfind('<script>')
script_end = content.rfind('</script>')
script = content[script_start:script_end]

# Contar llaves para ver si hay desbalance
opens = script.count('{')
closes = script.count('}')
print(f'Llaves abiertas: {opens}')
print(f'Llaves cerradas: {closes}')
print(f'Diferencia: {opens - closes}')

# Buscar el problema - funcion _loadIntelOld sin cerrar
idx = script.find('// removed')
if idx > 0:
    print('Texto despues de removed:', script[idx:idx+200])