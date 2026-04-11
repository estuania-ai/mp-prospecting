with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el toast actual en importarLeads
idx = content.find('Importando')
if idx == -1:
    idx = content.find('Importados')
print("Toast actual:", repr(content[idx:idx+100]))

# Reemplazar cualquier variante
for old_toast in [
    "toast('Importando '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');",
    "toast('Importados: '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');",
    "toast('Importados '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');"
]:
    if old_toast in content:
        content = content.replace(old_toast,
            "toast('Importados: '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');\n        if(r.ids) marcarImportacion(r.ids);"
        )
        print("Track OK")
        break

print("marcarImportacion:", 'marcarImportacion' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")