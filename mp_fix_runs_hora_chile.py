with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "    var fecha = (run.startedAt||'').substring(0,16).replace('T',' ');\n    var statusColor = run.status==='SUCCEEDED'?'#d4edda':'#fff3cd';\n    var statusText = run.status==='SUCCEEDED'?'Exitoso':'En proceso';"

new = """    // Convertir hora UTC a Chile (UTC-3)
    var fechaUTC = new Date(run.startedAt||'');
    var fechaChile = new Date(fechaUTC.getTime() - 3*60*60*1000);
    var fecha = fechaChile.toLocaleDateString('es-CL',{day:'2-digit',month:'2-digit',year:'numeric'}) + ' ' +
                fechaChile.toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'});
    var statusColor = run.status==='SUCCEEDED'?'#d4edda':'#fff3cd';
    var statusText = run.status==='SUCCEEDED'?'Exitoso':'En proceso';"""

if old in content:
    content = content.replace(old, new)
    print("Hora Chile OK")
else:
    print("No encontrado")

# Agregar leads insertados en el render del run
old_render = "        '<div style=\"font-size:11px;color:var(--mp-text-3);margin-top:2px\">'+fecha+' · '+run.itemCount+' items</div>' +"
new_render = "        '<div style=\"font-size:11px;color:var(--mp-text-3);margin-top:2px\">'+fecha+' (Chile) · '+run.itemCount+' items disponibles</div>' +"

if old_render in content:
    content = content.replace(old_render, new_render)
    print("Label items OK")
else:
    print("Label no encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test12.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")