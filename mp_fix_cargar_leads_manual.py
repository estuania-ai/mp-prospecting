"""
mp_fix_cargar_leads_manual.py
Agrega boton Cargar Leads en scraping para carga manual desde Apify
- Lista runs disponibles desde la cuenta Apify
- Permite seleccionar rubro y asignar categoria
- Respeta reglas: formato telefono 569X, comuna, rubro, categoria
- Registra en historial scraping
"""
with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar boton Cargar Leads en header de scraping
old_header = '''  <div class="page-header">
    <div class="page-title">Scraping Google Maps</div>
    <div class="page-sub">Obtener numeros de negocios via Apify</div>
  </div>'''

new_header = '''  <div class="page-header">
    <div class="page-title">Scraping Google Maps</div>
    <div class="page-sub">Obtener numeros de negocios via Apify</div>
    <button class="btn btn-ghost" onclick="abrirCargarLeads()" style="margin-left:auto">⬇ Cargar Leads</button>
  </div>'''

if old_header in content:
    content = content.replace(old_header, new_header)
    print("Boton Cargar Leads OK")
else:
    print("Header no encontrado")

# 2. Agregar modal Cargar Leads
modal_html = '''
<!-- Modal Cargar Leads Manual -->
<div class="modal-overlay" id="modalCargarLeads">
  <div class="modal" style="max-width:560px">
    <div class="modal-title">⬇ Cargar Leads desde Apify</div>
    <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">
      Selecciona un run de Apify para cargar sus leads al sistema
    </div>

    <div id="cargarLeadsRuns" style="max-height:200px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;margin-bottom:12px">
      <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
    </div>

    <div id="cargarLeadsForm" style="display:none">
      <div style="background:#e8f4fd;border-radius:8px;padding:10px 14px;margin-bottom:12px;font-size:12px">
        <div style="font-weight:700;color:var(--mp-blue)">Run seleccionado: <span id="cargarRunIdLabel"></span></div>
        <div style="color:var(--mp-text-3);margin-top:2px">Items encontrados: <span id="cargarRunItems"></span></div>
      </div>
      <div class="form-row">
        <label class="form-lbl">Rubro <span style="color:red">*</span></label>
        <select class="form-input" id="cargarRubro" onchange="onCargarRubroChange(this.value)">
          <option value="">Selecciona rubro...</option>
          <option value="almacen">Almacen</option>
          <option value="bazar">Jugueteria / Regalos</option>
          <option value="botilleria">Botilleria</option>
          <option value="cafeteria">Cafeteria</option>
          <option value="carniceria">Carniceria</option>
          <option value="clinica_dental">Clinica Dental</option>
          <option value="emporio">Emporio</option>
          <option value="farmacia">Farmacia</option>
          <option value="ferreteria">Ferreteria</option>
          <option value="fruteria">Fruteria</option>
          <option value="fuente_de_soda">Fuente de Soda</option>
          <option value="gimnasio">Gimnasio</option>
          <option value="lavanderia">Lavanderia</option>
          <option value="libreria">Libreria</option>
          <option value="minimarket">Minimarket</option>
          <option value="muebleria">Muebleria</option>
          <option value="panaderia">Panaderia</option>
          <option value="peluqueria">Peluqueria</option>
          <option value="pizzeria">Pizzeria</option>
          <option value="sandwicheria">Sandwicheria</option>
          <option value="spa">Spa</option>
          <option value="sushi">Sushi</option>
          <option value="taller">Taller</option>
          <option value="verduleria">Verduleria</option>
          <option value="veterinaria">Veterinaria</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-lbl">Categoria asignada</label>
        <input class="form-input" id="cargarCategoria" readonly style="background:#f8f9fa" placeholder="Se completa automaticamente">
      </div>
      <div class="form-row">
        <label class="form-lbl">Descripcion del scraping</label>
        <input class="form-input" id="cargarDescripcion" placeholder="Ej: Fruterias Las Condes">
      </div>
      <div id="cargarLeadsResult" style="display:none;margin-top:8px;padding:10px;border-radius:8px;font-size:12px"></div>
    </div>

    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalCargarLeads')">Cancelar</button>
      <button class="btn btn-primary" id="btnCargarLeadsOk" onclick="ejecutarCargarLeads()" style="display:none">⬇ Cargar Leads</button>
    </div>
  </div>
</div>
'''

if 'modalCargarLeads' not in content:
    content = content.replace('<!-- ─── CONFIGURACIÓN', modal_html + '<!-- ─── CONFIGURACIÓN')
    print("Modal Cargar Leads OK")

# 3. Agregar JS
js_fn = """
var cargarRunIdSeleccionado = null;
var cargarRunItemsTotal = 0;

var RUBRO_CAT_MAPA = {
  'almacen':'Comercio de Barrio Diario','bazar':'Retail Especializado y Hogar',
  'botilleria':'Comercio de Alta Demanda Fin de Semana','cafeteria':'Gastronomia y Comida Rapida',
  'carniceria':'Comercio de Alta Demanda Fin de Semana','clinica_dental':'Servicios de Alto Ticket',
  'emporio':'Comercio de Barrio Diario','farmacia':'Salud y Farmacia',
  'ferreteria':'Retail Especializado y Hogar','fruteria':'Comercio de Barrio Diario',
  'fuente_de_soda':'Gastronomia y Comida Rapida','gimnasio':'Membresias y Entrenamientos',
  'lavanderia':'Servicios Personales Diario','libreria':'Retail Especializado y Hogar',
  'minimarket':'Comercio de Barrio Diario','muebleria':'Retail Especializado y Hogar',
  'panaderia':'Comercio de Barrio Diario','peluqueria':'Servicios Personales Diario',
  'pizzeria':'Gastronomia y Comida Rapida','sandwicheria':'Gastronomia y Comida Rapida',
  'spa':'Servicios de Alto Ticket','sushi':'Gastronomia y Comida Rapida',
  'taller':'Servicios de Alto Ticket','verduleria':'Comercio de Barrio Diario',
  'veterinaria':'Servicios de Alto Ticket'
};

var COMUNAS_RM = ['Cerrillos','Cerro Navia','Conchalí','El Bosque','Estación Central',
  'Huechuraba','Independencia','La Cisterna','La Florida','La Granja','La Pintana',
  'La Reina','Las Condes','Lo Barnechea','Lo Espejo','Lo Prado','Macul','Maipú',
  'Ñuñoa','Peñalolén','Providencia','Pudahuel','Puente Alto','Quilicura',
  'Quinta Normal','Recoleta','Renca','San Bernardo','San Joaquín','San Miguel',
  'San Ramón','Santiago','Vitacura','Buin','Colina','El Monte','Lampa',
  'Melipilla','Paine','Pirque','Tiltil'];

function extraerComuna(address){
  if(!address) return '';
  var addrLower = address.toLowerCase();
  for(var i=0;i<COMUNAS_RM.length;i++){
    if(addrLower.indexOf(COMUNAS_RM[i].toLowerCase()) >= 0) return COMUNAS_RM[i];
  }
  return '';
}

function onCargarRubroChange(rubro){
  document.getElementById('cargarCategoria').value = RUBRO_CAT_MAPA[rubro] || '';
}

async function abrirCargarLeads(){
  cargarRunIdSeleccionado = null;
  document.getElementById('cargarLeadsForm').style.display = 'none';
  document.getElementById('btnCargarLeadsOk').style.display = 'none';
  document.getElementById('cargarLeadsResult').style.display = 'none';
  document.getElementById('modalCargarLeads').classList.add('open');
  document.getElementById('cargarLeadsRuns').innerHTML = '<div style="text-align:center;padding:20px"><div class="spinner"></div></div>';

  // Cargar runs desde Apify via backend
  var r = await api('/api/scraping/apify-runs');
  if(!r || !r.runs || !r.runs.length){
    document.getElementById('cargarLeadsRuns').innerHTML = '<div style="color:var(--mp-text-3);text-align:center;padding:16px">No hay runs disponibles. Verifica el token Apify.</div>';
    return;
  }

  document.getElementById('cargarLeadsRuns').innerHTML = r.runs.map(function(run){
    var fecha = (run.startedAt||'').substring(0,16).replace('T',' ');
    var statusColor = run.status==='SUCCEEDED'?'#d4edda':'#fff3cd';
    var statusText = run.status==='SUCCEEDED'?'Exitoso':'En proceso';
    return '<div onclick="seleccionarRun(\\''+run.id+'\\','+run.itemCount+')" style="padding:10px 14px;border-radius:8px;border:2px solid #eee;cursor:pointer;background:#fff;transition:all 0.2s" onmouseover="this.style.borderColor=\\'var(--mp-blue)\\'" onmouseout="this.style.borderColor=\\'#eee\\'">' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
      '<div>' +
      '<div style="font-size:12px;font-weight:700;color:var(--mp-text-1)">Run: '+run.id+'</div>' +
      '<div style="font-size:11px;color:var(--mp-text-3);margin-top:2px">'+fecha+' · '+run.itemCount+' items</div>' +
      '</div>' +
      '<span style="font-size:11px;padding:2px 10px;border-radius:8px;background:'+statusColor+';font-weight:600">'+statusText+'</span>' +
      '</div></div>';
  }).join('');
}

function seleccionarRun(runId, itemCount){
  cargarRunIdSeleccionado = runId;
  cargarRunItemsTotal = itemCount;
  document.getElementById('cargarRunIdLabel').textContent = runId;
  document.getElementById('cargarRunItems').textContent = itemCount;
  document.getElementById('cargarLeadsForm').style.display = 'block';
  document.getElementById('btnCargarLeadsOk').style.display = 'inline-block';
  document.getElementById('cargarRubro').value = '';
  document.getElementById('cargarCategoria').value = '';
  document.getElementById('cargarDescripcion').value = '';
  // Resaltar fila seleccionada
  var rows = document.getElementById('cargarLeadsRuns').querySelectorAll('div[onclick]');
  rows.forEach(function(r){ r.style.borderColor='#eee'; r.style.background='#fff'; });
  event.currentTarget.style.borderColor = 'var(--mp-blue)';
  event.currentTarget.style.background = '#e8f4fd';
}

async function ejecutarCargarLeads(){
  var rubro = document.getElementById('cargarRubro').value;
  var categoria = document.getElementById('cargarCategoria').value;
  var descripcion = document.getElementById('cargarDescripcion').value.trim();

  if(!rubro){ toast('Selecciona un rubro','error'); return; }
  if(!cargarRunIdSeleccionado){ toast('Selecciona un run','error'); return; }

  var btn = document.getElementById('btnCargarLeadsOk');
  btn.disabled = true; btn.textContent = '⏳ Cargando...';

  var r = await api('/api/scraping/cargar-leads', {
    method: 'POST',
    body: JSON.stringify({
      run_id: cargarRunIdSeleccionado,
      rubro: rubro,
      categoria: categoria,
      descripcion: descripcion || 'Carga manual'
    })
  });

  btn.disabled = false; btn.textContent = '⬇ Cargar Leads';

  var resultDiv = document.getElementById('cargarLeadsResult');
  resultDiv.style.display = 'block';

  if(r && r.ok){
    resultDiv.style.background = '#d4edda';
    resultDiv.style.color = '#155724';
    resultDiv.innerHTML = '✓ <strong>'+r.insertados+' leads insertados</strong> · '+r.duplicados+' duplicados · '+r.sin_telefono+' sin telefono valido';
    toast('Leads cargados: '+r.insertados+' nuevos', 'success');
    loadScrapingMetrics();
  } else {
    resultDiv.style.background = '#fff5f5';
    resultDiv.style.color = 'var(--mp-red)';
    resultDiv.innerHTML = '⚠ Error: '+(r&&r.error||'Error desconocido');
    toast('Error cargando leads','error');
  }
}

"""

if 'function abrirCargarLeads' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS Cargar Leads OK")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test12.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
