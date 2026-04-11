with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''<div style="padding:20px;margin-top:auto">
    <div style="background:var(--mp-blue-lt);border-radius:10px;padding:12px;border:1px solid #bee3f8">
      <div style="font-size:11px;font-weight:700;color:var(--mp-blue);margin-bottom:4px">Proximas tareas</div>
      <div style="font-size:12px;color:var(--mp-text-2)" id="nextSendTime">Calculando...</div>
      <div style="font-size:11px;color:var(--mp-text-3)" id="nextSendLabel"></div>
    </div>
  </div>

  <div class="sidebar-card" style="border-left:3px solid var(--mp-warn);margin-top:12px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <div class="sidebar-lbl">Tareas de Prospectos</div>
      <span id="tareasBadge" style="background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:1px 7px;border-radius:10px">0</span>
    </div>
    <div id="tareasWidget" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto">
      <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:8px">Sin tareas pendientes</div>
    </div>
    <button class="btn btn-ghost" onclick="showPage('interesados',document.querySelector('[onclick*=interesados]'),'Interesados')" style="width:100%;margin-top:8px;font-size:11px">Ver todas las tareas →</button>
  </div>'''

new = '''<div style="padding:20px;margin-top:auto">
    <div style="background:var(--mp-blue-lt);border-radius:10px;padding:12px;border:1px solid #bee3f8">
      <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
        <div style="font-size:11px;font-weight:700;color:var(--mp-blue)">Proximas tareas</div>
        <span id="tareasBadge" style="background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:1px 7px;border-radius:10px;display:none">0</span>
      </div>
      <div id="proximoEventosList" style="display:flex;flex-direction:column;gap:5px">
        <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:6px">Calculando...</div>
      </div>
      <div id="nextSendTime" style="display:none"></div>
      <div id="nextSendLabel" style="display:none"></div>
    </div>
  </div>'''

if old in content:
    content = content.replace(old, new)
    print("HTML reemplazado OK")
else:
    print("No encontrado")

# Actualizar updateNextSendTime para llenar proximoEventosList
old_fn_start = 'function updateNextSendTime(){'
idx = content.find(old_fn_start)
end = content.find('\n}', idx) + 2

new_fn = '''async function updateNextSendTime(){
  // Obtener tareas de prospectos
  var tareasProspectos = await api('/api/prospects/tasks/today') || [];
  var pendientes = tareasProspectos.filter(function(t){return !t.completada;});

  // Calcular proximos jobs del scheduler
  var now = new Date();
  var day = now.getDay();
  var h = now.getHours(), mi = now.getMinutes();
  var isWeekday = day >= 1 && day <= 5;
  var opts = {weekday:'short',day:'numeric',month:'short'};
  var jobItems = [];
  var horarios = [
    {h:9,m:30,label:'09:30',desc:'Prospeccion automatica - 15 msgs'},
    {h:15,m:0,label:'15:00',desc:'Prospeccion automatica - 10 msgs'},
    {h:17,m:30,label:'17:30',desc:'Prospeccion automatica - 15 msgs'}
  ];
  if(isWeekday){
    horarios.forEach(function(hor){
      if(h < hor.h || (h===hor.h && mi < hor.m)){
        jobItems.push({ico:'📤',titulo:'Prospeccion '+hor.label,desc:'Hoy a las '+hor.label,tipo:'job'});
      }
    });
  }
  // Agregar lunes siguiente si es fin de semana o ya pasaron todos los horarios
  if(jobItems.length === 0){
    var nextDate = new Date(now);
    do { nextDate.setDate(nextDate.getDate()+1); } while(nextDate.getDay()===0||nextDate.getDay()===6);
    jobItems.push({ico:'📤',titulo:'Prospeccion 09:30',desc:nextDate.toLocaleDateString('es-CL',opts)+' a las 09:30',tipo:'job'});
    jobItems.push({ico:'📤',titulo:'Prospeccion 15:00',desc:nextDate.toLocaleDateString('es-CL',opts)+' a las 15:00',tipo:'job'});
    jobItems.push({ico:'📤',titulo:'Prospeccion 17:30',desc:nextDate.toLocaleDateString('es-CL',opts)+' a las 17:30',tipo:'job'});
    jobItems.push({ico:'💌',titulo:'Fidelizacion Sellers',desc:'Lunes 11:00 AM - Etapas 7,14,15,30,35 dias',tipo:'job'});
  }

  // Combinar: max 6 total, min 2 tareas prospectos si hay mas de 4 jobs
  var maxJobs = pendientes.length >= 2 ? 4 : 6;
  var jobsShow = jobItems.slice(0, maxJobs);
  var tareasShow = pendientes.slice(0, 6 - jobsShow.length);

  // Actualizar badge
  if(pendientes.length > 0){
    document.getElementById('tareasBadge').style.display = 'inline';
    document.getElementById('tareasBadge').textContent = pendientes.length;
  }

  // Render lista
  var html = '';
  jobsShow.forEach(function(j){
    html += '<div style="display:flex;align-items:center;gap:6px;padding:5px 6px;border-radius:7px;background:rgba(0,158,227,0.08)">' +
      '<span style="font-size:13px">'+j.ico+'</span>' +
      '<div style="flex:1;min-width:0">' +
      '<div style="font-size:11px;font-weight:600;color:var(--mp-text-1)">'+j.titulo+'</div>' +
      '<div style="font-size:10px;color:var(--mp-text-3)">'+j.desc+'</div>' +
      '</div></div>';
  });

  tareasShow.forEach(function(t){
    var ico = {llamada:'📞',reunion:'🤝',seguimiento:'💬',visita:'🏪'}[t.tipo]||'📋';
    var atrasada = t.fecha < new Date().toISOString().slice(0,10);
    html += '<div onclick="showPage(\'interesados\',document.querySelector(\'[onclick*=interesados]\'),\'Interesados\')" style="display:flex;align-items:center;gap:6px;padding:5px 6px;border-radius:7px;background:'+(atrasada?'#fff5f5':'rgba(0,166,80,0.08)')+';cursor:pointer;border-left:2px solid '+(atrasada?'var(--mp-red)':'var(--mp-green)')+'">' +
      '<span style="font-size:13px">'+ico+'</span>' +
      '<div style="flex:1;min-width:0">' +
      '<div style="font-size:11px;font-weight:600;color:var(--mp-text-1)">'+t.negocio+'</div>' +
      '<div style="font-size:10px;color:var(--mp-text-3)">'+t.tipo+(t.hora?' · '+t.hora:'')+(atrasada?' · ⚠ Atrasada':'')+'</div>' +
      '</div></div>';
  });

  if(!html) html = '<div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:6px">Sin proximas tareas</div>';
  document.getElementById('proximoEventosList').innerHTML = html;
}'''

content = content[:idx] + new_fn + content[end:]

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)
print("proximoEventosList:", 'proximoEventosList' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")