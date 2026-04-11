with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar modal reagendar
idx = content.find('modalReagendar')
print("Modal reagendar pos:", idx)
print("Contexto:", content[idx:idx+400])
print()
# Buscar funcion confirmarReagendar
idx2 = content.find('function confirmarReagendar')
print("confirmarReagendar:", content[idx2:idx2+300])