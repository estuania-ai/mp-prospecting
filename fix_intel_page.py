with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    c = f.read()

intel_page = '''
<div class="page" id="page-intel">
  <div class="page-header">
    <div>
      <div class="page-title">Inteligencia de prospeccion</div>
      <div class="page-sub">Analisis de que rubros y comunas buscar para alimentar leads</div>
    </div>
    <button class="btn btn-primary" onclick="loadIntel()">Actualizar</button>
  </div>
  <div class="kpi-grid" style="grid-template-columns:repeat(4,1fr)">
    <div class="kpi" style="--kpi-color:var(--mp-blue)"><div class="kpi-label">Rubros con leads</div><div class="kpi-val" id="intel-rubros-con">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-red)"><div class="kpi-label">Rubros sin leads</div><div class="kpi-val" id="intel-rubros-sin">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-green)"><div class="kpi-label">Comunas cubiertas</div><div class="kpi-val" id="intel-comunas">0</div></div>
    <div class="kpi" style="--kpi-color:var(--mp-warn)"><div class="kpi-label">Sugerencias</div><div class="kpi-val" id="intel-sugerencias">0</div></div>
  </div>
  <div class="grid-2" style="margin-top:16px">
    <div class="card">
      <div class="card-title">Proximas busquedas recomendadas</div>
      <div id="nextSearches"><div style="text-align:center;padding:20px"><div class="spinner"></div></div></div>
    </div>
    <div class="card">
      <div class="card-title">Acciones urgentes</div>
      <div id="intelSuggestions"><div style="text-align:center;padding:20px"><div class="spinner"></div></div></div>
    </div>
  </div>
  <div class="grid-2" style="margin-top:0">
    <div class="card">
      <div class="card-title">Rendimiento por rubro</div>
      <div class="table-wrap">
        <table><thead><tr><th>Rubro</th><th>Leads</th><th>Enviados</th><th>Interesados</th><th>Tasa</th></tr></thead>
        <tbody id="intelRubrosTable"></tbody></table>
      </div>
    </div>
    <div class="card">
      <div class="card-title">Cobertura por comuna</div>
      <div id="intelComunas" style="display:flex;flex-direction:column;gap:8px;max-height:300px;overflow-y:auto"></div>
    </div>
  </div>
</div>
'''

intel_js = '''
async function loadIntel(){
  const [s, n] = await Promise.all([api('/api/intel/suggestions'), api('/api/intel/next-searches')]);
  if(!s) return;
  document.getElementById('intel-rubros-con').textContent = s.resumen.total_rubros_con_leads;
  document.getElementById('intel-rubros-sin').textContent = s.resumen.total_rubros_sin_leads;
  document.getElementById('intel-comunas').textContent = s.resumen.comunas_cubiertas;
  document.getElementById('intel-sugerencias').textContent = s.resumen.sugerencias_pendientes;
  document.getElementById('intelSuggestions').innerHTML = s.suggestions.length
    ? s.suggestions.map(x=>`<div class="log-item"><div class="log-info"><div class="log-title">${x.mensaje}</div><div class="log-meta">Query: ${x.query_sugerida}</div></div><span class="badge ${x.prioridad==="alta"?"badge-no":"badge-interesado"}">${x.prioridad}</span></div>`).join('')
    : '<div style="color:var(--mp-text-3);padding:20px;text-align:center">Base bien cubierta</div>';
  if(n?.next_searches?.length){
    document.getElementById('nextSearches').innerHTML = n.next_searches.slice(0,8).map(x=>`<div class="log-item"><div class="log-info"><div class="log-title">${x.rubro_label} en ${x.comuna}</div><div class="log-meta">${x.razon}</div></div><a href="${x.maps_url_base}" target="_blank" class="btn btn-ghost btn-sm">Maps</a></div>`).join('');
  } else {
    document.getElementById('nextSearches').innerHTML = '<div style="color:var(--mp-text-3);padding:20px;text-align:center">Agrega mas leads para ver recomendaciones</div>';
  }
  const maxL = Math.max(...s.rubro_stats.map(r=>r.total_leads),1);
  document.getElementById('intelRubrosTable').innerHTML = s.rubro_stats.map(r=>{
    const t=r.enviados>0?Math.round(r.interesados/r.enviados*100):0;
    return `<tr><td>${r.rubro}</td><td>${r.total_leads}</td><td>${r.enviados}</td><td style="color:var(--mp-warn);font-weight:600">${r.interesados}</td><td style="color:${t>10?"var(--mp-green)":"var(--mp-text-3)"};font-weight:600">${t}%</td></tr>`;
  }).join('');
  const maxC = Math.max(...s.comuna_stats.map(c=>c.total_leads),1);
  document.getElementById('intelComunas').innerHTML = s.comuna_stats.map(c=>`<div class="commune-row"><div class="commune-name">${c.comuna}</div><div class="commune-track"><div class="commune-bar" style="width:${Math.round(c.total_leads/maxC*100)}%"></div></div><div class="commune-val">${c.total_leads}</div></div>`).join('');
}
'''

# Insertar pagina antes del cierre del main
if 'page-intel' not in c:
    c = c.replace('</div><!-- /main -->', intel_page + '</div><!-- /main -->')

# Insertar JS antes del cierre del script
if 'loadIntel' not in c:
    c = c.replace('</script>', intel_js + '\n</script>')

# Agregar intel al loader de paginas
if 'intel: loadIntel' not in c:
    c = c.replace('config: loadConfig,', 'config: loadConfig,\n    intel: loadIntel,')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(c)
print('OK - pagina intel agregada')