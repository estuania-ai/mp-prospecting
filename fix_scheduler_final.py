with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Corregir nombres del scheduler
old = "'prospecting_daily' ? 'Prospección L-V (09:30 · 15:00 · 17:30)' : 'Fidelización Lunes 11:00 AM'"
new = """(function(id){
          var names = {
            'batch_0930':'Prospeccion 09:30 AM - 15 mensajes',
            'batch_1500':'Prospeccion 15:00 PM - 10 mensajes',
            'batch_1730':'Prospeccion 17:30 PM - 15 mensajes',
            'fidelizacion_weekly':'Fidelizacion Sellers - Lunes 11:00 AM',
            'prospecting_daily':'Prospeccion L-V'
          };
          return names[id] || id;
        })(j.id)"""
content = content.replace(old, new)
print("Scheduler names OK:", 'batch_0930' in content)

# 2. Corregir subtitulo del scheduler
old2 = "Próximo: ${j.next_run||'—'}"
new2 = """(function(j){
            var nextDate = j.next_run ? new Date(j.next_run) : null;
            var nextStr = nextDate ? nextDate.toLocaleDateString('es-CL',{weekday:'short',day:'numeric',month:'short'}) + ' ' + nextDate.toLocaleTimeString('es-CL',{hour:'2-digit',minute:'2-digit'}) : 'Sin programar';
            var isFidel = j.id === 'fidelizacion_weekly';
            var sub = isFidel ? nextStr + ' · Mensajes dias 7,14,15,30,35 desde cierre' : nextStr + ' · Leads con estado no enviado';
            return sub;
          })(j)"""
content = content.replace(old2, new2)
print("Subtitulo OK:", 'no enviado' in content)

# 3. Corregir updateNextSendTime
old3 = """function updateNextSendTime(){
  const now = new Date();
  const day = now.getDay();
  const h = now.getHours(), mi = now.getMinutes();
  const isWeekday = day >= 1 && day <= 5;
  let label, time;

  if(isWeekday && (h < 10 || (h===10 && mi===0))){
    time = 'Hoy a las 10:00 AM';
    label = 'Prospección';
  } else {
    const days = isWeekday ? (5 - day === 0 && h>=10 ? 3 : 5-day + (h>=10?1:0)) : (day===6?2:1);
    time = `En ${days} día${days>1?'s':''}`;
    label = 'Próxima prospección';
  }

  document.getElementById('nextSendTime').textContent = time;
  document.getElementById('nextSendLabel').textContent = label;
}"""

new3 = """function updateNextSendTime(){
  var now = new Date();
  var day = now.getDay();
  var h = now.getHours(), mi = now.getMinutes();
  var isWeekday = day >= 1 && day <= 5;
  var horarios = [{h:9,m:30,label:'09:30'},{h:15,m:0,label:'15:00'},{h:17,m:30,label:'17:30'}];
  var nextTime = '', nextLabel = 'Proxima prospeccion';
  var opts = {weekday:'long',day:'numeric',month:'long'};

  if(isWeekday){
    var proxHoy = null;
    for(var i=0;i<horarios.length;i++){
      if(h < horarios[i].h || (h===horarios[i].h && mi < horarios[i].m)){
        proxHoy = horarios[i]; break;
      }
    }
    if(proxHoy){
      nextTime = 'Hoy ' + now.toLocaleDateString('es-CL',opts) + ' a las ' + proxHoy.label;
    } else {
      var nextDate = new Date(now);
      do { nextDate.setDate(nextDate.getDate()+1); } while(nextDate.getDay()===0||nextDate.getDay()===6);
      nextDate.setHours(9,30,0,0);
      nextTime = nextDate.toLocaleDateString('es-CL',opts) + ' a las 09:30';
    }
  } else {
    var dias = day===6?2:1;
    var nextDate2 = new Date(now);
    nextDate2.setDate(now.getDate()+dias);
    nextDate2.setHours(9,30,0,0);
    nextTime = nextDate2.toLocaleDateString('es-CL',opts) + ' a las 09:30';
  }

  document.getElementById('nextSendTime').textContent = nextTime;
  document.getElementById('nextSendLabel').textContent = nextLabel;
}"""

content = content.replace(old3, new3)
print("NextSendTime OK:", 'proxHoy' in content)

# 4. Agregar intel si no existe
if 'page-intel' not in content:
    intel_page = '<div class="page" id="page-intel"><div class="page-header"><div><div class="page-title">Inteligencia de prospeccion</div><div class="page-sub">Criterios de envio + donde buscar nuevos leads</div></div><button class="btn btn-primary" onclick="loadIntel()">Actualizar</button></div><div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px"><div class="kpi" style="--kpi-color:var(--mp-blue)"><div class="kpi-label">Rubros con leads</div><div class="kpi-val" id="intel-rubros-con">0</div></div><div class="kpi" style="--kpi-color:var(--mp-red)"><div class="kpi-label">Rubros sin leads</div><div class="kpi-val" id="intel-rubros-sin">0</div></div><div class="kpi" style="--kpi-color:var(--mp-green)"><div class="kpi-label">Comunas cubiertas</div><div class="kpi-val" id="intel-comunas">0</div></div><div class="kpi" style="--kpi-color:var(--mp-warn)"><div class="kpi-label">Acciones urgentes</div><div class="kpi-val" id="intel-sugerencias">0</div></div></div><div class="grid-2" style="margin-bottom:0"><div class="card"><div class="card-title">Criterio de envio por rubro</div><div class="table-wrap" style="max-height:280px;overflow-y:auto"><table><thead><tr><th>Rubro</th><th>Leads</th><th>Enviados</th><th>Interesados</th><th>Tasa</th><th>Prioridad</th></tr></thead><tbody id="intelRubrosTable"><tr><td colspan="6" style="text-align:center;padding:20px"><div class="spinner"></div></td></tr></tbody></table></div></div><div class="card"><div class="card-title">Tasa por comuna</div><div id="intelComunas" style="display:flex;flex-direction:column;gap:8px;max-height:280px;overflow-y:auto"><div style="text-align:center;padding:20px"><div class="spinner"></div></div></div></div></div><div class="grid-2" style="margin-top:0"><div class="card"><div class="card-title">Donde buscar nuevos leads</div><div id="intelSuggestions" style="display:flex;flex-direction:column;gap:8px;max-height:280px;overflow-y:auto"><div style="text-align:center;padding:20px"><div class="spinner"></div></div></div></div><div class="card"><div class="card-title">Proximas busquedas recomendadas</div><div id="nextSearches" style="display:flex;flex-direction:column;gap:8px;max-height:280px;overflow-y:auto"><div style="text-align:center;padding:20px"><div class="spinner"></div></div></div></div></div><div class="card" style="margin-top:0"><div class="card-title">Rubros sin leads todavia</div><div id="intelRubrosSin" style="display:flex;flex-wrap:wrap;gap:8px;padding:8px 0"><div style="text-align:center;padding:20px;width:100%"><div class="spinner"></div></div></div></div></div>'
    content = content.replace('<div class="page" id="page-scraping">', intel_page + '\n<div class="page" id="page-scraping">')
    print("Intel page OK")

if 'Inteligencia' not in content:
    content = content.replace(
        'onclick="showPage(\'config\'',
        'onclick="showPage(\'intel\',this,\'Inteligencia\')"><span class="nav-icon">*</span> Inteligencia</div>\n  <div class="nav-item" onclick="showPage(\'config\''
    )
    print("Intel nav OK")

if 'intel: loadIntel' not in content:
    content = content.replace('config: loadConfig,', 'config: loadConfig,\n    intel: loadIntel,')

if 'function loadIntel' not in content:
    intel_js = "\nasync function loadIntel(){var s=await api('/api/intel/suggestions');var n=await api('/api/intel/next-searches');if(!s)return;document.getElementById('intel-rubros-con').textContent=s.resumen.total_rubros_con_leads;document.getElementById('intel-rubros-sin').textContent=s.resumen.total_rubros_sin_leads;document.getElementById('intel-comunas').textContent=s.resumen.comunas_cubiertas;document.getElementById('intel-sugerencias').textContent=s.resumen.sugerencias_pendientes;document.getElementById('intelRubrosTable').innerHTML=s.rubro_stats.map(function(r){var tasa=r.enviados>0?Math.round(r.interesados/r.enviados*100):0;var pri,pc,pb;if(tasa>=15){pri='ALTA';pc='#155724';pb='#d4edda';}else if(tasa>=5){pri='MEDIA';pc='#856404';pb='#fff3cd';}else if(r.pendientes>0){pri='NORMAL';pc='#0c5460';pb='#d1ecf1';}else{pri='BAJA';pc='#6c757d';pb='#f8f9fa';}return '<tr><td><span style=\"font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px\">'+r.rubro+'</span></td><td style=\"text-align:center\">'+r.total_leads+'</td><td style=\"text-align:center\">'+r.enviados+'</td><td style=\"text-align:center;color:var(--mp-warn);font-weight:600\">'+r.interesados+'</td><td style=\"text-align:center;font-weight:700;color:'+(tasa>=10?'var(--mp-green)':'var(--mp-text-3)')+'\">'+tasa+'%</td><td style=\"text-align:center\"><span style=\"padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;background:'+pb+';color:'+pc+'\">'+pri+'</span></td></tr>';}).join('')||'<tr><td colspan=\"6\" style=\"text-align:center;padding:20px;color:var(--mp-text-3)\">Sin datos aun</td></tr>';var maxC=Math.max.apply(null,s.comuna_stats.map(function(c){return c.total_leads;}));if(maxC<=0)maxC=1;document.getElementById('intelComunas').innerHTML=s.comuna_stats.length?s.comuna_stats.map(function(c){var tasa=c.total_leads>0?Math.round((c.interesados||0)/c.total_leads*100):0;return '<div class=\"commune-row\"><div class=\"commune-name\" style=\"min-width:120px\">'+c.comuna+'</div><div class=\"commune-track\" style=\"flex:1\"><div class=\"commune-bar\" style=\"width:'+Math.round(c.total_leads/maxC*100)+'%\"></div></div><div class=\"commune-val\">'+c.total_leads+'</div>'+(tasa>0?'<span style=\"margin-left:8px;font-size:11px;font-weight:700;color:var(--mp-warn)\">'+tasa+'%</span>':'')+(c.interesados>0?'<span style=\"font-size:10px;color:var(--mp-green);margin-left:4px\">'+c.interesados+' int.</span>':'')+'</div>';}).join(''):'<div style=\"color:var(--mp-text-3);padding:20px;text-align:center\">Sin datos</div>';document.getElementById('intelSuggestions').innerHTML=s.suggestions.length?s.suggestions.map(function(sg){return '<div class=\"log-item\" style=\"border-left:3px solid '+(sg.prioridad==='alta'?'var(--mp-red)':'var(--mp-warn)')+'\"><div class=\"log-info\"><div class=\"log-title\">'+sg.mensaje+'</div><div class=\"log-meta\">Buscar: \"'+sg.query_sugerida+'\"</div></div><span class=\"badge '+(sg.prioridad==='alta'?'badge-no':'badge-interesado')+'\">'+sg.prioridad+'</span></div>';}).join(''):'<div style=\"color:var(--mp-text-3);padding:20px;text-align:center\">Base bien cubierta</div>';if(n&&n.next_searches&&n.next_searches.length){document.getElementById('nextSearches').innerHTML=n.next_searches.slice(0,8).map(function(x){return '<div class=\"log-item\"><div class=\"log-info\"><div class=\"log-title\">'+x.rubro_label+' en '+x.comuna+'</div><div class=\"log-meta\">'+x.razon+'</div></div><a href=\"'+x.maps_url_base+'\" target=\"_blank\" class=\"btn btn-ghost btn-sm\">Maps</a></div>';}).join('');}else{document.getElementById('nextSearches').innerHTML='<div style=\"color:var(--mp-text-3);padding:20px;text-align:center\">Agrega leads para ver recomendaciones</div>';}document.getElementById('intelRubrosSin').innerHTML=s.rubros_sin_leads.length?s.rubros_sin_leads.map(function(r){return '<span style=\"display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;background:#fff3e0;color:#e65100;font-size:12px;font-weight:600;border:1px solid #ffcc80\">'+r.emoji+' '+r.label+'</span>';}).join(''):'<span style=\"color:var(--mp-text-3);font-size:13px\">Todos los rubros tienen leads</span>';}\n"
    content = content.replace('setInterval(checkWaStatus, 30000);', intel_js + 'setInterval(checkWaStatus, 30000);')
    print("Intel JS OK")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")