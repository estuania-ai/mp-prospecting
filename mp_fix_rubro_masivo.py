with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar checkbox "aplicar a todos" en ambas secciones del modal
old_asignar_img = '      <div style="font-size:11px;color:var(--mp-text-3)">La imagen del mensaje correspondera a esta categoria</div>'
new_asignar_img = '''      <div style="font-size:11px;color:var(--mp-text-3)">La imagen del mensaje correspondera a esta categoria</div>
      <div style="margin-top:10px;background:#e8f4fd;border-radius:8px;padding:8px 12px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="aplicarTodosAsignar" checked style="width:15px;height:15px;cursor:pointer">
        <label for="aplicarTodosAsignar" style="font-size:12px;font-weight:600;color:var(--mp-blue);cursor:pointer">Aplicar a todos los leads con este rubro</label>
      </div>'''

old_nuevo_img = '        ✓ Se usara el mensaje universal y la imagen de la categoria seleccionada'
new_nuevo_img = '''        ✓ Se usara el mensaje universal y la imagen de la categoria seleccionada
      </div>
      <div style="margin-top:8px;background:#f0fff4;border-radius:8px;padding:8px 12px;display:flex;align-items:center;gap:8px">
        <input type="checkbox" id="aplicarTodosNuevo" checked style="width:15px;height:15px;cursor:pointer">
        <label for="aplicarTodosNuevo" style="font-size:12px;font-weight:600;color:#276749;cursor:pointer">Aplicar a todos los leads con este rubro</label>'''

if old_asignar_img in content:
    content = content.replace(old_asignar_img, new_asignar_img)
    print("Checkbox asignar OK")
else:
    print("Checkbox asignar no encontrado")

if old_nuevo_img in content:
    content = content.replace(old_nuevo_img, new_nuevo_img)
    print("Checkbox nuevo OK")
else:
    print("Checkbox nuevo no encontrado")

# Actualizar guardarCorreccionRubro para enviar rubro original y aplicar_todos
old_guardar_api = """  var r = await api('/api/leads/'+leadId+'/update-rubro', {
    method:'PUT',
    body: JSON.stringify({rubro:rubro, categoria:categoria})
  });
  if(r&&r.ok){
    toast('Rubro actualizado correctamente','success');
    closeModal('modalCorregirRubro');
    loadLeads();
  } else toast('Error actualizando rubro','error');
}"""

new_guardar_api = """  var rubroOriginal = document.getElementById('corregirRubroOriginal').value;
  var aplicarTodos = seccionActiva==='asignar' ?
    document.getElementById('aplicarTodosAsignar').checked :
    document.getElementById('aplicarTodosNuevo').checked;

  var r = await api('/api/leads/'+leadId+'/update-rubro', {
    method:'PUT',
    body: JSON.stringify({rubro:rubro, categoria:categoria, rubro_original:rubroOriginal, aplicar_todos:aplicarTodos})
  });
  if(r&&r.ok){
    var msg = aplicarTodos ? 'Rubro actualizado en '+r.actualizados+' leads' : 'Rubro actualizado correctamente';
    toast(msg,'success');
    closeModal('modalCorregirRubro');
    loadLeads();
  } else toast('Error actualizando rubro','error');
}"""

if old_guardar_api in content:
    content = content.replace(old_guardar_api, new_guardar_api)
    print("JS guardar masivo OK")
else:
    print("guardar api no encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")