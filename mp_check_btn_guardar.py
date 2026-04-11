with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el boton guardar del modal
idx = content.find('id="modalStatus"')
end = content.find('</div>\n</div>', idx) + 15
modal = content[idx:end]
print("Boton guardar:", 'submitStatus' in modal)

# Buscar modal-actions
idx2 = modal.find('modal-actions')
print("Modal actions:", modal[idx2:idx2+200])

# Buscar si hay submitStatus comentado
commented = content.count('// submitStatus')
print("submitStatus comentado:", commented, "veces")