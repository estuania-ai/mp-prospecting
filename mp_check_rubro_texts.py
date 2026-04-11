with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar rubrosValidos
idx = content.find('rubrosValidos')
print("rubrosValidos:")
print(repr(content[idx:idx+200]))
print()

# Buscar toast despues de guardar
idx2 = content.find('Rubro actualizado en')
print("Toast guardar:")
print(repr(content[idx2-20:idx2+150]))