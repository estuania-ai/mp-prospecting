with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''  <div class="sidebar-card" style="border-left:3px solid var(--mp-warn);margin-top:12px">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:8px">
      <div class="sidebar-lbl">Tareas de Prospectos</div>
      <span id="tareasBadge" style="background:var(--mp-warn);color:#fff;font-size:10px;font-weight:700;padding:1px 7px;border-radius:10px">0</span>
    </div>
    <div id="tareasWidget" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto">
      <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:8px">Sin tareas pendientes</div>
    </div>
    <button class="btn btn-ghost" onclick="showPage('interesados',document.querySelector('[onclick*=interesados]'),'Interesados')" style="width:100%;margin-top:8px;font-size:11px">Ver todas las tareas →</button>
  </div>'''

new = '''  <div style="margin-top:12px;background:linear-gradient(135deg,#009ee3 0%,#0077b6 100%);border-radius:12px;padding:14px;box-shadow:0 2px 8px rgba(0,158,227,0.25)">
    <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:10px">
      <div style="color:#fff;font-size:12px;font-weight:700;letter-spacing:0.3px">📋 Tareas de Prospectos</div>
      <span id="tareasBadge" style="background:rgba(255,255,255,0.25);color:#fff;font-size:11px;font-weight:800;padding:2px 8px;border-radius:20px;min-width:20px;text-align:center">0</span>
    </div>
    <div id="tareasWidget" style="display:flex;flex-direction:column;gap:5px;max-height:220px;overflow-y:auto">
      <div style="font-size:11px;color:rgba(255,255,255,0.7);text-align:center;padding:10px">Sin tareas pendientes hoy</div>
    </div>
    <div style="margin-top:10px;border-top:1px solid rgba(255,255,255,0.2);padding-top:10px;display:flex;gap:6px">
      <button onclick="showPage(\'interesados\',document.querySelector(\'[onclick*=interesados]\'),\'Interesados\')" style="flex:1;background:rgba(255,255,255,0.2);color:#fff;border:none;border-radius:8px;padding:6px;font-size:11px;font-weight:600;cursor:pointer">Ver agenda →</button>
      <button onclick="showPage(\'interesados\',document.querySelector(\'[onclick*=interesados]\'),\'Interesados\')" style="flex:1;background:#00a650;color:#fff;border:none;border-radius:8px;padding:6px;font-size:11px;font-weight:600;cursor:pointer">+ Nueva tarea</button>
    </div>
  </div>'''

if old in content:
    content = content.replace(old, new)
    print("Widget actualizado OK")
else:
    print("No encontrado - verificando...")
    idx = content.find('tareasWidget')
    print("tareasWidget pos:", idx)
    print("Contexto:", repr(content[idx-200:idx+50]))

# Mejorar renderTareasWidget JS para colores corporativos
old_render = '''function renderTareasWidget(tasks){
  var pendientes = tasks.filter(function(t){return !t.completada;});
  if(!pendientes.length){
    document.getElementById('tareasWidget').innerHTML = '<div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:8px">Sin tareas pendientes hoy</div>';
    return;
  }
  document.getElementById('tareasWidget').innerHTML = pendientes.slice(0,5).map(function(t){
    var icoTipo = {llamada:'📞',reunion:'🤝',seguimiento:'💬',visita:'🏪'}[t.tipo] || '📋';
    var atrasada = t.fecha < new Date().toISOString().slice(0,10);
    return '<div style="background:'+(atrasada?'#fff5f5':'#f8f9fa')+';border-radius:8px;padding:8px 10px;font-size:11px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
      '<span style="font-weight:600;color:'+(atrasada?'var(--mp-red)':'var(--mp-text-1)')+'">'+icoTipo+' '+t.negocio+'</span>' +
      '<div style="display:flex;gap:4px">' +
      '<button onclick="event.stopPropagation();completarTareaWidget('+t.id+')" style="background:var(--mp-green);color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px">✓</button>' +
      '<button onclick="event.stopPropagation();abrirReagendar('+t.id+')" style="background:var(--mp-blue-lt);color:var(--mp-blue);border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px">↻</button>' +
      '<a href="https://wa.me/'+t.phone+'?text=Hola+'+encodeURIComponent(t.name)+'!" target="_blank" style="background:#25D366;color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px;text-decoration:none">💬</a>' +
      '</div></div>' +
      '<div style="color:var(--mp-text-3);margin-top:2px">'+t.tipo+' · '+(t.hora||'')+' · '+(t.fecha||'')+'</div>' +
      '</div>';
  }).join('');
}'''

new_render = '''function renderTareasWidget(tasks){
  var pendientes = tasks.filter(function(t){return !t.completada;});
  if(!pendientes.length){
    document.getElementById('tareasWidget').innerHTML = '<div style="font-size:11px;color:rgba(255,255,255,0.6);text-align:center;padding:10px">Sin tareas pendientes hoy ✓</div>';
    return;
  }
  document.getElementById('tareasBadge').textContent = pendientes.length;
  document.getElementById('tareasWidget').innerHTML = pendientes.slice(0,5).map(function(t){
    var icoTipo = {llamada:'📞',reunion:'🤝',seguimiento:'💬',visita:'🏪'}[t.tipo] || '📋';
    var atrasada = t.fecha < new Date().toISOString().slice(0,10);
    return '<div style="background:'+(atrasada?'rgba(242,61,79,0.2)':'rgba(255,255,255,0.12)')+';border-radius:8px;padding:8px 10px;border-left:3px solid '+(atrasada?'#f23d4f':'rgba(255,255,255,0.4)');font-size:11px">' +
      '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">' +
      '<span style="font-weight:700;color:#fff;font-size:11px">'+icoTipo+' '+t.negocio+'</span>' +
      '<div style="display:flex;gap:3px">' +
      '<button onclick="event.stopPropagation();completarTareaWidget('+t.id+')" title="Completar" style="background:#00a650;color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px;font-weight:700">✓</button>' +
      '<button onclick="event.stopPropagation();abrirReagendar('+t.id+')" title="Reagendar" style="background:rgba(255,255,255,0.2);color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px">↻</button>' +
      '<a href="https://wa.me/'+t.phone.replace(/\D/g,'')+'" target="_blank" title="WhatsApp" style="background:#25D366;color:#fff;border:none;border-radius:6px;padding:2px 6px;cursor:pointer;font-size:10px;text-decoration:none;display:inline-block">💬</a>' +
      '</div></div>' +
      '<div style="color:rgba(255,255,255,0.65);font-size:10px">'+(atrasada?'⚠ Atrasada · ':'')+t.tipo+' · '+(t.hora||'Sin hora')+' · '+(t.fecha||'')+'</div>' +
      '</div>';
  }).join('');
}'''

if old_render in content:
    content = content.replace(old_render, new_render)
    print("Render widget OK")
else:
    print("Render no encontrado - se mantiene el actual")

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")