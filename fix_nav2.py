with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    c = f.read()

# Limpiar el nav roto
c = c.replace(
    '<div class="nav-item" onclick="showPage(\'intel\',this,\'Inteligencia\')"><span class="nav-icon">*</span> Inteligencia</div>\n  onclick="showPage(\'config\'',
    '<div class="nav-item" onclick="showPage(\'intel\',this,\'Inteligencia\')"><span class="nav-icon">*</span> Inteligencia</div>\n  <div class="nav-item" onclick="showPage(\'config\''
)

# Limpiar el texto suelto onclick que aparece en el sidebar
c = c.replace('\n  onclick="showPage(\'config\'', '\n  <div class="nav-item" onclick="showPage(\'config\'')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK - nav corregido')