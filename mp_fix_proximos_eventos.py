with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Cambiar titulo Scheduler -> Proximos eventos
old_title = '<div class="card-title"><span class="card-icon">⚙️</span>Scheduler</div>'
new_title = '<div class="card-title"><span class="card-icon">📅</span>Proximos eventos</div>'
content = content.replace(old_title, new_title)
print("Titulo OK:", 'Proximos eventos' in content)

# 2. Agregar seccion tareas del dia despues de schedulerJobs
old_scheduler_end = '<div id="schedulerJobs">\n        <div style="text-align:center;padding:20px"><div class="spinner'
new_scheduler_end = '''<div id="schedulerJobs">
        <div style="text-align:center;padding:20px"><div class="spinner'''

# 3. Agregar div tareasHoy despues del card schedulerJobs
old_card_end = '</div>\n      </div>\n    </div>\n\n    <div class="card">\n      <div class="card-title"><span class="card-icon">📋</span>Configuración de envío</div>'
new_card_end = '''</div>
      </div>
      <div style="border-top:1px solid var(--mp-border);margin-top:8px;padding-top:8px">
        <div style="font-size:11px;font-weight:600;color:var(--mp-text-2);margin-bottom:6px">📋 Tareas de prospectos hoy</div>
        <div id="tareasHoyEnvios">
          <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:6px">Sin tareas para hoy</div>
        </div>
      </div>
    </div>

    <div class="card">
      <div class="card-title"><span class="card-icon">📋</span>Configuración de envío</div>'''

if old_card_end in content:
    content = content.replace(old_card_end, new_card_end)
    print("Seccion tareas OK:", 'tareasHoyEnvios' in content)
else:
    print("No encontrado - buscando alternativa...")
    idx = content.find('Configuración de envío')
    print("Config envio pos:", idx)
    print("Contexto:", repr(content[idx-200:idx+50]))

# 4. Agregar render de tareas en loadEnvios JS
old_load_envios_end = "  if(campaigns?.length){"
new_load_envios_end = """  // Tareas del dia en proximos eventos
  if(document.getElementById('tareasHoyEnvios')){
    var tareasHoy = await api('/api/prospects/tasks/today');
    if(tareasHoy && tareasHoy.length){
      document.getElementById('tareasHoyEnvios').innerHTML = tareasHoy.slice(0,4).map(function(t){
        var ico = {llamada:'📞',reunion:'🤝',seguimiento:'💬',visita:'🏪'}[t.tipo]||'📋';
        var atrasada = t.fecha < new Date().toISOString().slice(0,10);
        return '<div onclick="showPage(\\'interesados\\',document.querySelector(\\'[onclick*=interesados]\\'),\\'Interesados\\')" style="display:flex;align-items:center;gap:8px;padding:6px 8px;border-radius:8px;background:'+(atrasada?'#fff5f5':'#f8f9fa')+';margin-bottom:4px;cursor:pointer;border-left:3px solid '+(atrasada?'var(--mp-red)':'var(--mp-warn)')+'">' +
          '<span style="font-size:13px">'+ico+'</span>' +
          '<div style="flex:1;min-width:0">' +
          '<div style="font-size:11px;font-weight:600;color:var(--mp-text-1);white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+t.negocio+'</div>' +
          '<div style="font-size:10px;color:var(--mp-text-3)">'+t.tipo+(t.hora?' · '+t.hora:'')+'</div>' +
          '</div>' +
          (atrasada?'<span style="font-size:9px;background:#f23d4f;color:#fff;padding:1px 5px;border-radius:6px">Atrasada</span>':'') +
          '</div>';
      }).join('');
    } else {
      document.getElementById('tareasHoyEnvios').innerHTML = '<div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:6px">Sin tareas para hoy ✓</div>';
    }
  }

  if(campaigns?.length){"""

if old_load_envios_end in content:
    content = content.replace(old_load_envios_end, new_load_envios_end)
    print("JS tareas en loadEnvios OK")
else:
    print("loadEnvios end no encontrado")
    idx = content.find('if(campaigns?.length)')
    print("campaigns pos:", idx)

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")