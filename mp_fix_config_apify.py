with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar seccion Apify Token con version mejorada
old = '''      <div class="cfg-row">
        <div><div class="cfg-lbl">Apify Token</div><div class="cfg-desc">Para Google Maps scraping</div></div>
        <input class="cfg-input" type="password" id="cfg-apify_token" placeholder="apify_api_...">
      </div>
      <div class="cfg-row">
        <div><div class="cfg-lbl">Google Calendar link</div>'''

new = '''      <div class="cfg-row">
        <div><div class="cfg-lbl">Apify Token</div><div class="cfg-desc">Para Google Maps scraping</div></div>
        <div style="display:flex;gap:8px;align-items:center">
          <input class="cfg-input" type="password" id="cfg-apify_token" placeholder="apify_api_..." oninput="onApifyTokenChange()">
          <button onclick="cargarActoresApify()" style="background:var(--mp-blue);color:#fff;border:none;border-radius:8px;padding:6px 14px;cursor:pointer;font-size:12px;white-space:nowrap;font-weight:600">🔍 Cargar actores</button>
        </div>
      </div>
      <div id="apifyActorSection" style="display:none;margin-top:4px">
        <div class="cfg-row">
          <div>
            <div class="cfg-lbl">Actor de Google Maps</div>
            <div class="cfg-desc">Selecciona el actor disponible en tu cuenta</div>
          </div>
          <select class="cfg-input" id="cfg-apify_actor_id" style="min-width:250px">
            <option value="">Cargando actores...</option>
          </select>
        </div>
        <div id="apifyStatusMsg" style="font-size:11px;padding:6px 10px;border-radius:6px;margin-top:4px"></div>
      </div>
      <div class="cfg-row">
        <div><div class="cfg-lbl">Google Calendar link</div>'''

if old in content:
    content = content.replace(old, new)
    print("Seccion Apify OK")
else:
    print("No encontrado")

# Agregar JS para cargar actores
js_fn = """
function onApifyTokenChange(){
  // Ocultar actores cuando cambia el token
  document.getElementById('apifyActorSection').style.display = 'none';
}

function cargarActoresApify(){
  var token = document.getElementById('cfg-apify_token').value.trim();
  if(!token){ toast('Ingresa el token Apify primero','error'); return; }

  var btn = event.target;
  btn.textContent = '⏳ Cargando...';
  btn.disabled = true;

  // Guardar token temporalmente para validar
  api('/api/config', {method:'POST', body:JSON.stringify({'apify_token': token})}).then(function(){
    return api('/api/scraping/validate-token', {method:'POST'});
  }).then(function(r){
    btn.textContent = '🔍 Cargar actores';
    btn.disabled = false;

    var section = document.getElementById('apifyActorSection');
    var statusMsg = document.getElementById('apifyStatusMsg');
    var select = document.getElementById('cfg-apify_actor_id');
    section.style.display = 'block';

    if(!r || !r.ok){
      statusMsg.style.background = '#fff5f5';
      statusMsg.style.color = 'var(--mp-red)';
      statusMsg.textContent = '⚠ ' + (r&&r.error||'Token invalido');
      select.innerHTML = '<option value="">Token invalido</option>';
      return;
    }

    if(r.actor_ok){
      statusMsg.style.background = '#d4edda';
      statusMsg.style.color = '#155724';
      statusMsg.textContent = '✓ Token valido - Usuario: '+r.user+' - Actor actual: '+r.actor_nombre;
    } else {
      statusMsg.style.background = '#fff3cd';
      statusMsg.style.color = '#856404';
      statusMsg.textContent = '⚠ Token valido pero el actor actual no existe en esta cuenta. Selecciona uno de la lista.';
    }

    // Llenar select con actores disponibles
    var actores = r.actores_disponibles || [];
    // Agregar actor actual si existe
    if(r.actor_ok){
      select.innerHTML = '<option value="'+r.actor_id+'">✓ '+r.actor_nombre+' (actual)</option>';
    } else {
      select.innerHTML = '<option value="">Selecciona actor de Google Maps...</option>';
    }

    // Agregar actores de la cuenta
    actores.forEach(function(a){
      var opt = document.createElement('option');
      opt.value = a.full;
      opt.textContent = a.full;
      select.appendChild(opt);
    });

    // Agregar opcion manual
    var optManual = document.createElement('option');
    optManual.value = 'compass/google-maps-extractor';
    optManual.textContent = 'compass/google-maps-extractor (default)';
    select.appendChild(optManual);

  }).catch(function(e){
    btn.textContent = '🔍 Cargar actores';
    btn.disabled = false;
    toast('Error conectando con Apify','error');
  });
}
"""

if 'function cargarActoresApify' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS cargarActoresApify OK")
else:
    print("JS ya existe")

# Asegurar que al cargar config se muestre el actor actual
old_load_config = "document.getElementById('cfg-apify_token').value = d.apify_token||'';"
new_load_config = """document.getElementById('cfg-apify_token').value = d.apify_token||'';
  // Mostrar actor actual si existe
  if(d.apify_actor_id){
    var section = document.getElementById('apifyActorSection');
    var select = document.getElementById('cfg-apify_actor_id');
    var statusMsg = document.getElementById('apifyStatusMsg');
    if(section) section.style.display = 'block';
    if(select) select.innerHTML = '<option value="'+d.apify_actor_id+'">'+d.apify_actor_id+'</option>';
    if(statusMsg){
      statusMsg.style.background = '#e8f4fd';
      statusMsg.style.color = 'var(--mp-blue)';
      statusMsg.textContent = 'Actor configurado: '+d.apify_actor_id;
    }
  }"""

if old_load_config in content:
    content = content.replace(old_load_config, new_load_config)
    print("Load config actor OK")
else:
    print("load config no encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test12.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")