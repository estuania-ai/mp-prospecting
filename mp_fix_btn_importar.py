with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '<button class="btn btn-ghost btn-sm" onclick="exportLeads()">⬇ Exportar</button>'
new = '<button class="btn btn-ghost btn-sm" onclick="exportLeads()">⬇ Exportar</button>\n          <button class="btn btn-ghost btn-sm" onclick="document.getElementById(\'importFile\').click()">⬆ Importar</button>\n          <input type="file" id="importFile" accept=".xlsx" style="display:none" onchange="importarLeads(this)">'

if old in content:
    content = content.replace(old, new)
    print("Boton importar OK")
else:
    print("No encontrado")

print("importarLeads:", 'function importarLeads' in content)
print("SheetJS:", 'xlsx.full.min' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")