with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "      var telefono = (row[colTelefono]||'').toString().trim().replace(/\\s/g,'');"
new = """      var telefono = (row[colTelefono]||'').toString().trim().replace(/\\s/g,'').replace(/[^0-9]/g,'');
      // Agregar 56 si no tiene codigo de pais
      if(telefono.length === 9 && telefono.startsWith('9')){
        telefono = '56' + telefono;
      } else if(telefono.length === 11 && telefono.startsWith('569')){
        // ya tiene 56 correcto
      } else if(telefono.startsWith('+')){
        telefono = telefono.replace('+','');
      }"""

if old in content:
    content = content.replace(old, new)
    print("Phone format OK")
else:
    print("No encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")