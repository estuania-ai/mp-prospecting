with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Ver CSS sidebar-card
idx = content.find('.sidebar-card')
print("=== CSS sidebar-card ===")
print(content[idx:idx+300])
print()

# Ver estructura del card Proximo envio
idx2 = content.find('Proximo envio')
start = content.rfind('<div class="sidebar-card"', 0, idx2)
print("=== Card Proximo envio ===")
print(content[start:start+500])
print()

# Ver widget Tareas actual
idx3 = content.find('Tareas de Prospectos')
start3 = content.rfind('<div class="sidebar-card"', 0, idx3)
print("=== Widget Tareas actual ===")
print(content[start3:start3+400])