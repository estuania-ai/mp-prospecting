with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar nav item
if 'Inteligencia' not in content:
    content = content.replace(
        'onclick="showPage(\'config\'',
        'onclick="showPage(\'intel\',this,\'Inteligencia\')"><span class="nav-icon">*</span> Inteligencia</div>\n  <div class="nav-item" onclick="showPage(\'config\''
    )
    print('Nav OK')

# 2. Agregar pagina intel antes de scraping
if 'page-intel' not in content:
    intel = '''<div class="page" id="page-intel">
  <div class="page-header">
    <div><div class="page-title">Inteligencia de prospeccion</div>
    <div class="page-sub">Criterios de envio + donde buscar nuevos leads</div></div>
    <button class="btn btn-primary" onclick="loadIntel()">Actualizar</button>
  </div>
  <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr);margin-bottom:16px">
    <div class="kpi" style="--kpi-color:var(--mp-blue)"><div class="kpi-label">Rubros con leads</div><div class="kpi-val" id="intel-rubros-con">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-red)"><div class="kpi-label">Rubros sin leads</div><div class="kpi-val" id="intel-rubros-sin">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-green)"><div class="kpi-label">Comunas cubiertas</div><div class="kpi-val" id="intel-comunas">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-warn)"><div class="kpi-label">Acciones urgentes</div><div class="kpi-val" id="intel-sugerencias">0</div></div>
  </div>
  <div class="grid-2" style="margin-bottom:0">
    <div class="card">
      <div class="card-title">Criterio de envio por rubro</div>
      <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">Prioridad segun tasa de respuesta</div>
      <div class="table-wrap" style="max-height:280px;overflow-y:auto">
        <table><thead><tr><th>Rubro</th><th>Leads</th><th>Enviados</th><th>Interesados</th><th>Tasa</th><th>Prioridad</th></tr></thead>
        <tbody id="intelRubrosTable"><tr><td colspan="6" style="text-align:center;padding:20px"><div class="spinner"></div></td></tr></tbody></table>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Tasa de respuesta por comuna</div>
      <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">Comunas con mas interes = enviar primero ahi</div>
      <div id="intelComunas" style="display:flex;flex-direction:column;gap:8px;max-height:280px;overflow-y:auto">
        <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
      </div>
    </div>
  </div>
  <div class="grid-2" style="margin-top:0">
    <div class="card">
      <div class="card-title">Donde buscar nuevos leads</div>
      <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">Rubros con pocos leads o sin cobertura</div>
      <div id="intelSuggestions" style="display:flex;flex-direction:column;gap:8px;max-height:280px;overflow-y:auto">
        <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Proximas busquedas recomendadas</div>
      <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">Mejores rubros x comunas con link a Maps</div>
      <div id="nextSearches" style="display:flex;flex-direction:column;gap:8px;max-height:280px;overflow-y:auto">
        <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
      </div>
    </div>
  </div>
  <div class="card" style="margin-top:0">
    <div class="card-title">Rubros sin ningun lead todavia</div>
    <div id="intelRubrosSin" style="display:flex;flex-wrap:wrap;gap:8px;padding:8px 0">
      <div style="text-align:center;padding:20px;width:100%"><div class="spinner"></div></div>
    </div>
  </div>
</div>

'''
    content = content.replace('<div class="page" id="page-scraping">', intel + '<div class="page" id="page-scraping">')
    print('Page OK')

# 3. Agregar intel al loader de paginas
if 'intel: loadIntel' not in content:
    content = content.replace('config: loadConfig,', 'config: loadConfig,\n    intel: loadIntel,')
    print('Loader OK')

# 4. Agregar funcion loadIntel antes del cierre del script
if 'function loadIntel' not in content:
    intel_js = '''
async function loadIntel(){
  const [s, n] = await Promise.all([api('/api/intel/suggestions'), api('/api/intel/next-searches')]);
  if(!s) return;
  document.getElementById('intel-rubros-con').textContent = s.resumen.total_rubros_con_leads;
  document.getElementById('intel-rubros-sin').textContent = s.resumen.total_rubros_sin_leads;
  document.getElementById('intel-comunas').textContent = s.resumen.comunas_cubiertas;
  document.getElementById('intel-sugerencias').textContent = s.resumen.sugerencias_pendientes;
  document.getElementById('intelRubrosTable').innerHTML = s.rubro_stats.map(function(r){
    var tasa = r.enviados > 0 ? Math.round(r.interesados/r.enviados*100) : 0;
    var pri, pc, pb;
    if(tasa>=15){pri='ALTA';pc='#155724';pb='#d4edda';}
    else if(tasa>=5){pri='MEDIA';pc='#856404';pb='#fff3cd';}
    else if(r.pendientes>0){pri='NORMAL';pc='#0c5460';pb='#d1ecf1';}
    else{pri='BAJA';pc='#6c757d';pb='#f8f9fa';}
    return '<tr><td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">'+r.rubro+'</span></td><td style="text-align:center">'+r.total_leads+'</td><td style="text-align:center">'+r.enviados+'</td><td style="text-align:center;color:var(--mp-warn);font-weight:600">'+r.interesados+'</td><td style="text-align:center;font-weight:700;color:'+(tasa>=10?'var(--mp-green)':'var(--mp-text-3)')+'">'+tasa+'%</td><td style="text-align:center"><span style="padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;background:'+pb+';color:'+pc+'">'+pri+'</span></td></tr>';
  }).join('') || '<tr><td colspan="6" style="text-align:center;padding:20px;color:var(--mp-text-3)">Sin datos aun</td></tr>';
  var maxC = Math.max.apply(null, s.comuna_stats.map(function(c){return c.total_leads;}));
  if(maxC<=0) maxC=1;
  document.getElementById('intelComunas').innerHTML = s.comuna_stats.length ? s.comuna_stats.map(function(c){
    var tasa = c.total_leads > 0 ? Math.round((c.interesados||0)/c.total_leads*100) : 0;
    return '<div class="commune-row"><div class="commune-name" style="min-width:120px">'+c.comuna+'</div><div class="commune-track" style="flex:1"><div class="commune-bar" style="width:'+Math.round(c.total_leads/maxC*100)+'%"></div></div><div class="commune-val">'+c.total_leads+'</div>'+(tasa>0?'<span style="margin-left:8px;font-size:11px;font-weight:700;color:var(--mp-warn)">'+tasa+'%</span>':'')+(c.interesados>0?'<span style="font-size:10px;color:var(--mp-green);margin-left:4px">'+c.interesados+' int.</span>':'')+'</div>';
  }).join('') : '<div style="color:var(--mp-text-3);padding:20px;text-align:center">Sin datos de comunas aun</div>';
  document.getElementById('intelSuggestions').innerHTML = s.suggestions.length ? s.suggestions.map(function(sg){
    return '<div class="log-item" style="border-left:3px solid '+(sg.prioridad==='alta'?'var(--mp-red)':'var(--mp-warn)')+'"><div class="log-info"><div class="log-title">'+sg.mensaje+'</div><div class="log-meta">Buscar: "'+sg.query_sugerida+'"</div></div><span class="badge '+(sg.prioridad==='alta'?'badge-no':'badge-interesado')+'">'+sg.prioridad+'</span></div>';
  }).join('') : '<div style="color:var(--mp-text-3);padding:20px;text-align:center">Base bien cubierta</div>';
  if(n && n.next_searches && n.next_searches.length){
    document.getElementById('nextSearches').innerHTML = n.next_searches.slice(0,8).map(function(x){
      return '<div class="log-item"><div class="log-info"><div class="log-title">'+x.rubro_label+' en '+x.comuna+'</div><div class="log-meta">'+x.razon+'</div></div><a href="'+x.maps_url_base+'" target="_blank" class="btn btn-ghost btn-sm">Maps</a></div>';
    }).join('');
  } else {
    document.getElementById('nextSearches').innerHTML = '<div style="color:var(--mp-text-3);padding:20px;text-align:center">Agrega leads para ver recomendaciones</div>';
  }
  document.getElementById('intelRubrosSin').innerHTML = s.rubros_sin_leads.length ? s.rubros_sin_leads.map(function(r){
    return '<span style="display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;background:#fff3e0;color:#e65100;font-size:12px;font-weight:600;border:1px solid #ffcc80">'+r.emoji+' '+r.label+'</span>';
  }).join('') : '<span style="color:var(--mp-text-3);font-size:13px">Todos los rubros tienen leads</span>';
}

'''
    content = content.replace('setInterval(checkWaStatus, 30000);', intel_js + 'setInterval(checkWaStatus, 30000);')
    print('JS OK')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('LISTO - dashboard actualizado')