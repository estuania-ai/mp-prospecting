"""
mp_fix_scraping_dashboard.py
Agrega en pestaña Scraping:
1. Historial de runs con detalle
2. Metricas: Leads por rubro y cobertura por comuna
3. Alerta al cambiar token Apify
"""
with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar seccion metricas y historial al final de la pagina scraping
old_end = '</div>\n\n<!-- ─── INTEL'
if '</div>\n\n<!-- ─── INTEL' not in content:
    old_end = '</div>\n\n<!-- ─── CONFIG'

# Buscar el final de la pagina scraping
idx_scraping = content.find('page-scraping')
idx_next = content.find('<!-- ─── ', idx_scraping + 100)
scraping_end = content.rfind('</div>', idx_scraping, idx_next)

new_sections = '''

  <!-- Metricas Leads -->
  <div class="grid-2" style="margin-top:0">
    <div class="card">
      <div class="card-title"><span class="card-icon">📊</span>Leads por rubro</div>
      <div style="font-size:11px;color:var(--mp-text-3);margin-bottom:8px">Total de leads prospectados por rubro</div>
      <div id="scraLeadsPorRubro" style="max-height:250px;overflow-y:auto;display:flex;flex-direction:column;gap:5px">
        <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span class="card-icon">🏙️</span>Cobertura por comuna</div>
      <div style="font-size:11px;color:var(--mp-text-3);margin-bottom:8px">Distribucion geografica de leads</div>
      <div id="scraLeadsPorComuna" style="max-height:250px;overflow-y:auto;display:flex;flex-direction:column;gap:5px">
        <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
      </div>
    </div>
  </div>

  <!-- Historial scraping -->
  <div class="card" style="margin-top:0">
    <div class="card-title"><span class="card-icon">📋</span>Historial de scrapings</div>
    <div style="font-size:11px;color:var(--mp-text-3);margin-bottom:8px">Registro de todos los scrapings ejecutados</div>
    <div class="table-wrap" style="border-radius:8px;max-height:300px;overflow-y:auto">
      <table>
        <thead><tr>
          <th>Fecha</th>
          <th>Tipo</th>
          <th>Rubro</th>
          <th>Comuna/URL</th>
          <th style="text-align:center">Encontrados</th>
          <th style="text-align:center">Insertados</th>
          <th style="text-align:center">Duplicados</th>
          <th style="text-align:center">Estado</th>
        </tr></thead>
        <tbody id="scraHistorial">
          <tr><td colspan="8" style="text-align:center;padding:20px"><div class="spinner"></div></td></tr>
        </tbody>
      </table>
    </div>
  </div>

'''

content = content[:scraping_end] + new_sections + content[scraping_end:]
print("1. Secciones metricas e historial OK")

# 2. Agregar alerta token en config
old_apify_save = "saveConfig()"
# Buscar donde se guarda el token de apify en config
idx_config = content.find("apify_token")
print("apify_token pos:", idx_config)

# 3. Agregar JS para cargar metricas e historial
js_fn = """
async function loadScrapingMetrics(){
  var [metrics, history] = await Promise.all([
    api('/api/scraping/metrics'),
    api('/api/scraping/history')
  ]);

  // Metricas por rubro
  if(metrics && metrics.por_rubro && document.getElementById('scraLeadsPorRubro')){
    var maxR = Math.max.apply(null, metrics.por_rubro.map(function(r){return r.total;}));
    if(maxR<=0) maxR=1;
    document.getElementById('scraLeadsPorRubro').innerHTML = metrics.por_rubro.length ?
      metrics.por_rubro.map(function(r){
        var pct = Math.round(r.total/maxR*100);
        var tasa = r.enviados > 0 ? Math.round(r.interesados/r.enviados*100) : 0;
        return '<div style="margin-bottom:8px">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">' +
          '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1)">'+r.rubro+'</span>' +
          '<div style="display:flex;gap:4px">' +
          '<span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:1px 8px;border-radius:8px">'+r.total+'</span>' +
          (tasa>0?'<span style="font-size:11px;background:#fff3cd;color:#856404;padding:1px 8px;border-radius:8px">'+tasa+'% int.</span>':'') +
          '</div></div>' +
          '<div style="background:#eef2f7;border-radius:4px;height:6px;overflow:hidden">' +
          '<div style="height:100%;border-radius:4px;background:var(--mp-blue);width:'+pct+'%"></div>' +
          '</div></div>';
      }).join('') :
      '<div style="color:var(--mp-text-3);text-align:center;padding:12px">Sin datos aun</div>';
  }

  // Metricas por comuna
  if(metrics && metrics.por_comuna && document.getElementById('scraLeadsPorComuna')){
    var maxC = Math.max.apply(null, metrics.por_comuna.map(function(c){return c.total;}));
    if(maxC<=0) maxC=1;
    document.getElementById('scraLeadsPorComuna').innerHTML = metrics.por_comuna.length ?
      metrics.por_comuna.slice(0,10).map(function(c){
        var pct = Math.round(c.total/maxC*100);
        var tasa = c.enviados > 0 ? Math.round(c.interesados/c.enviados*100) : 0;
        return '<div style="margin-bottom:8px">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:3px">' +
          '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1)">'+c.comuna+'</span>' +
          '<div style="display:flex;gap:4px">' +
          '<span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:1px 8px;border-radius:8px">'+c.total+'</span>' +
          (tasa>0?'<span style="font-size:11px;background:#d4edda;color:#155724;padding:1px 8px;border-radius:8px">'+tasa+'% int.</span>':'') +
          '</div></div>' +
          '<div style="background:#eef2f7;border-radius:4px;height:6px;overflow:hidden">' +
          '<div style="height:100%;border-radius:4px;background:var(--mp-green);width:'+pct+'%"></div>' +
          '</div></div>';
      }).join('') :
      '<div style="color:var(--mp-text-3);text-align:center;padding:12px">Sin datos de comunas</div>';
  }

  // Historial
  if(history && document.getElementById('scraHistorial')){
    document.getElementById('scraHistorial').innerHTML = history.length ?
      history.map(function(h){
        var statusColor = h.status==='succeeded'?'badge-cerrado':h.status==='running'?'badge-interesado':'badge-no';
        var statusLabel = h.status==='succeeded'?'Exitoso':h.status==='running'?'Corriendo':'Fallido';
        var ubicacion = h.tipo==='url' ? (h.maps_url||'').substring(0,40)+'...' : (h.comuna||'—');
        return '<tr>' +
          '<td style="font-size:11px">'+(h.started_at||'').substring(0,16)+'</td>' +
          '<td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:1px 6px;border-radius:6px">'+(h.tipo==='url'?'URL':'Busqueda')+'</span></td>' +
          '<td style="font-size:11px">'+(h.rubro||'—')+'</td>' +
          '<td style="font-size:11px;max-width:150px;overflow:hidden;text-overflow:ellipsis" title="'+ubicacion+'">'+ubicacion+'</td>' +
          '<td style="text-align:center;font-weight:700">'+(h.leads_found||0)+'</td>' +
          '<td style="text-align:center;color:var(--mp-green);font-weight:700">'+(h.leads_inserted||0)+'</td>' +
          '<td style="text-align:center;color:var(--mp-text-3)">'+(h.leads_skipped||0)+'</td>' +
          '<td style="text-align:center"><span class="badge '+statusColor+'">'+statusLabel+'</span></td>' +
          '</tr>';
      }).join('') :
      '<tr><td colspan="8" style="text-align:center;padding:16px;color:var(--mp-text-3)">Sin historial aun</td></tr>';
  }
}

// Validar token Apify al cambiar
function validarTokenApify(){
  api('/api/scraping/validate-token', {method:'POST'}).then(function(r){
    if(r && r.ok){
      toast('Token Apify valido - Usuario: '+r.user, 'success');
    } else {
      toast('⚠ Token Apify INVALIDO: '+(r&&r.error||'Error desconocido'), 'error');
      // Resaltar campo token
      var input = document.getElementById('cfg-apify-token');
      if(input) input.style.border = '2px solid var(--mp-red)';
    }
  });
}

"""

if 'function loadScrapingMetrics' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("2. JS metricas OK")

# 4. Agregar al loader de scraping
if 'scraping: loadScraping' in content:
    old_loader = 'scraping: loadScraping,'
    new_loader = 'scraping: function(){ loadScraping(); loadScrapingMetrics(); },'
    content = content.replace(old_loader, new_loader)
    print("3. Loader scraping actualizado OK")

# 5. Agregar boton validar token en seccion config apify
old_apify_field = 'id="cfg-apify-token"'
if old_apify_field in content:
    idx = content.find(old_apify_field)
    end = content.find('</div>', idx) + 6
    old_block = content[idx-200:end]
    print("4. Campo token encontrado OK")

with open('templates/dashboard_test11.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
