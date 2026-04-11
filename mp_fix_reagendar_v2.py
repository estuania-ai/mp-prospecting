with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Revertir async en confirmarReagendar
content = content.replace(
    'async function confirmarReagendar(){',
    'function confirmarReagendar(){'
)

# Reemplazar el await por then
old = """function confirmarReagendar(){
  var tid = document.getElementById('reagendarTaskId').value;
  var fecha = document.getElementById('reagendarFecha').value;
  if(!fecha){ toast('Selecciona una fecha','error'); return; }
  var r = await api('/api/prospects/tasks/'+tid+'/reagendar', {
    method:'PUT',
    body:JSON.stringify({
      fecha: fecha,
      hora: document.getElementById('reagendarHora').value,
      nota: document.getElementById('reagendarNota').value
    })
  });
  if(r&&r.ok){
    toast('Tarea reagendada','success');
    closeModal('modalReagendar');
    loadInteresados();
  } else toast('Error','error');
}"""

new = """function confirmarReagendar(){
  var tid = document.getElementById('reagendarTaskId').value;
  var fecha = document.getElementById('reagendarFecha').value;
  if(!fecha){ toast('Selecciona una fecha','error'); return; }
  api('/api/prospects/tasks/'+tid+'/reagendar', {
    method:'PUT',
    body:JSON.stringify({
      fecha: fecha,
      hora: document.getElementById('reagendarHora').value,
      nota: document.getElementById('reagendarNota').value
    })
  }).then(function(r){
    if(r&&r.ok){
      toast('Tarea reagendada','success');
      closeModal('modalReagendar');
      loadInteresados();
    } else toast('Error reagendando','error');
  });
}"""

if old in content:
    content = content.replace(old, new)
    print("Reagendar fix OK")
else:
    print("No encontrado - buscando...")
    idx = content.find('function confirmarReagendar')
    end = content.find('\n}', idx) + 2
    print(repr(content[idx:end]))

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test7.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")