with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Actualizar cargarActoresApify para auto-seleccionar el actor de Google Maps
old_actores = """    // Llenar select con actores disponibles
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
    select.appendChild(optManual);"""

new_actores = """    // Llenar select con actores disponibles
    var actores = r.actores_disponibles || [];

    if(r.actor_ok){
      select.innerHTML = '<option value="'+r.actor_id+'">✓ '+r.actor_nombre+' (actual)</option>';
    } else {
      select.innerHTML = '<option value="">Selecciona actor de Google Maps...</option>';
    }

    actores.forEach(function(a){
      var opt = document.createElement('option');
      opt.value = a.full;
      opt.textContent = a.full;
      select.appendChild(opt);
    });

    // Auto-seleccionar si hay exactamente 1 actor de Google Maps
    if(!r.actor_ok && actores.length === 1){
      select.value = actores[0].full;
      // Guardar automaticamente
      api('/api/scraping/set-actor', {method:'POST', body:JSON.stringify({actor_id: actores[0].full})}).then(function(){
        statusMsg.style.background = '#d4edda';
        statusMsg.style.color = '#155724';
        statusMsg.textContent = '✓ Actor seleccionado automaticamente: '+actores[0].full;
      });
    } else if(!r.actor_ok && actores.length === 0){
      // Buscar por ID directo en Apify usando runs recientes
      api('/api/scraping/detect-actor', {method:'POST'}).then(function(det){
        if(det && det.actor_id){
          var opt = document.createElement('option');
          opt.value = det.actor_id;
          opt.textContent = '✓ '+det.actor_id+' (detectado automaticamente)';
          opt.selected = true;
          select.appendChild(opt);
          statusMsg.style.background = '#d4edda';
          statusMsg.style.color = '#155724';
          statusMsg.textContent = '✓ Actor detectado desde historial: '+det.actor_id;
        } else {
          var optManual = document.createElement('option');
          optManual.value = '2Mdma1N6Fd0y3QEjR';
          optManual.textContent = 'Google Maps Extractor (2Mdma1N6Fd0y3QEjR)';
          select.appendChild(optManual);
        }
      });
    }"""

if old_actores in content:
    content = content.replace(old_actores, new_actores)
    print("Auto-deteccion OK")
else:
    print("No encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test12.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")