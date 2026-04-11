"""
mp_fix_token_alerta.py
Agrega alerta automatica al cambiar token Apify en Configuracion
- Valida token al guardar
- Verifica que el actor existe en la nueva cuenta
- Si no existe, muestra actores disponibles para seleccionar
"""
with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar campo actor ID en configuracion si no existe
old_apify_section = 'id="cfg-apify-token"'
idx = content.find(old_apify_section)
print("cfg-apify-token pos:", idx)

# Buscar el div completo de la seccion apify
start = content.rfind('<div class="cfg-row">', 0, idx)
end = content.find('</div>\n      <div class="cfg-row">', idx)
if end == -1:
    end = content.find('</div>\n    </div>', idx)
print("Seccion apify:")
print(content[start:start+300])

# 2. Agregar banner de alerta token en scraping
old_scraping_header = '''  <div class="page-header">
    <div class="page-title">Scraping Google Maps</div>
    <div class="page-sub">Obtener números de negocios vía Apify</div>
  </div>'''

new_scraping_header = '''  <div class="page-header">
    <div class="page-title">Scraping Google Maps</div>
    <div class="page-sub">Obtener numeros de negocios via Apify</div>
  </div>

  <div id="alertaToken" style="display:none;background:#fff5f5;border:1px solid #ffd0d0;border-radius:10px;padding:12px 16px;margin-bottom:16px">
    <div style="display:flex;justify-content:space-between;align-items:center">
      <div>
        <div style="font-size:13px;font-weight:700;color:var(--mp-red)">⚠ Problema con el token Apify</div>
        <div id="alertaTokenMsg" style="font-size:12px;color:#856404;margin-top:4px"></div>
      </div>
      <button onclick="validarTokenApify()" style="background:var(--mp-blue);color:#fff;border:none;border-radius:8px;padding:6px 14px;cursor:pointer;font-size:12px;font-weight:600">Validar ahora</button>
    </div>
    <div id="alertaActores" style="display:none;margin-top:10px;border-top:1px solid #ffd0d0;padding-top:10px">
      <div style="font-size:12px;font-weight:600;color:var(--mp-text-2);margin-bottom:6px">Actores disponibles en tu cuenta:</div>
      <div id="listaActores" style="display:flex;flex-direction:column;gap:4px"></div>
    </div>
  </div>'''

if old_scraping_header in content:
    content = content.replace(old_scraping_header, new_scraping_header)
    print("Banner alerta token OK")
else:
    print("Header scraping no encontrado")

# 3. Actualizar funcion validarTokenApify con logica completa
old_fn = """function validarTokenApify(){
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
}"""

new_fn = """function validarTokenApify(){
  toast('Validando token Apify...','');
  api('/api/scraping/validate-token', {method:'POST'}).then(function(r){
    var alerta = document.getElementById('alertaToken');
    var alertaMsg = document.getElementById('alertaTokenMsg');
    var alertaActores = document.getElementById('alertaActores');
    
    if(!r || !r.ok){
      toast('Token Apify invalido: '+(r&&r.error||'Error'), 'error');
      if(alerta){ alerta.style.display='block'; }
      if(alertaMsg){ alertaMsg.textContent = r&&r.error || 'Token invalido'; }
      return;
    }

    if(r.actor_ok){
      toast('Token OK - Usuario: '+r.user+' - Actor: '+r.actor_nombre, 'success');
      if(alerta) alerta.style.display='none';
      // Limpiar borde rojo
      var input = document.getElementById('cfg-apify-token');
      if(input) input.style.border = '';
    } else {
      // Token OK pero actor no existe
      toast('⚠ Token valido pero actor no encontrado en esta cuenta', 'error');
      if(alerta) alerta.style.display='block';
      if(alertaMsg) alertaMsg.textContent = r.alerta || 'El actor no existe en esta cuenta';
      
      // Mostrar actores disponibles
      if(r.actores_disponibles && r.actores_disponibles.length && alertaActores){
        alertaActores.style.display='block';
        document.getElementById('listaActores').innerHTML = r.actores_disponibles.map(function(a){
          return '<div style="display:flex;justify-content:space-between;align-items:center;padding:6px 10px;background:#fff;border-radius:6px;border:1px solid #eee">' +
            '<span style="font-size:12px;font-weight:600">'+a.full+'</span>' +
            '<button onclick="seleccionarActor(\\''+a.full+'\\')" style="background:var(--mp-blue);color:#fff;border:none;border-radius:6px;padding:3px 10px;cursor:pointer;font-size:11px">Usar este</button>' +
            '</div>';
        }).join('');
      } else if(alertaActores){
        alertaActores.style.display='block';
        document.getElementById('listaActores').innerHTML = '<div style="font-size:12px;color:var(--mp-text-3)">No se encontraron actores de Google Maps. Ve a apify.com y agrega el actor "compass/google-maps-extractor"</div>';
      }
    }
  });
}

function seleccionarActor(actorId){
  api('/api/scraping/set-actor', {method:'POST', body:JSON.stringify({actor_id:actorId})}).then(function(r){
    if(r&&r.ok){
      toast('Actor actualizado: '+actorId, 'success');
      document.getElementById('alertaToken').style.display='none';
    }
  });
}"""

if old_fn in content:
    content = content.replace(old_fn, new_fn)
    print("validarTokenApify actualizado OK")
else:
    print("funcion no encontrada - agregando...")
    if 'function validarTokenApify' not in content:
        content = content.replace('setInterval(checkWaStatus, 30000);', new_fn + '\nsetInterval(checkWaStatus, 30000);')
        print("JS agregado OK")

# 4. Agregar validacion automatica al guardar config
old_save = """async function saveConfig(){
  const data = {};"""

new_save = """async function saveConfig(){
  const data = {};"""

# Buscar donde se guarda el token para agregar validacion posterior
idx_save = content.find('async function saveConfig()')
if idx_save > 0:
    # Encontrar el return de saveConfig
    end_save = content.find('\n}', idx_save) + 2
    save_fn = content[idx_save:end_save]
    
    if 'apify_token' in save_fn and 'validarTokenApify' not in save_fn:
        # Agregar validacion al final de saveConfig
        old_end = "  if(r?.ok){ toast('Configuración guardada','success'); }"
        new_end = """  if(r?.ok){
    toast('Configuracion guardada','success');
    // Si cambio el token Apify, validar automaticamente
    var tokenField = document.getElementById('cfg-apify-token');
    if(tokenField) {
      setTimeout(function(){
        validarTokenApify();
      }, 500);
    }
  }"""
        if old_end in content:
            content = content.replace(old_end, new_end)
            print("Auto-validacion al guardar OK")

# 5. Validar token al cargar la pagina de scraping
old_load_scraping = "scraping: function(){ loadScraping(); loadScrapingMetrics(); },"
new_load_scraping = "scraping: function(){ loadScraping(); loadScrapingMetrics(); setTimeout(validarTokenApify, 1000); },"

if old_load_scraping in content:
    content = content.replace(old_load_scraping, new_load_scraping)
    print("Auto-validacion al abrir scraping OK")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test12.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
