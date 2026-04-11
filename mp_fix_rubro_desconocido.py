with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar badge de alerta en tabla leads para rubros no reconocidos
old_rubro_td = """      <td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">${l.rubro||'—'}</span></td>"""

new_rubro_td = """      <td>
        ${(function(){
          var rubrosValidos = ['almacen','bazar','botilleria','cafeteria','carniceria','clinica_dental','emporio','farmacia','ferreteria','fruteria','fuente_de_soda','gimnasio','lavanderia','libreria','minimarket','muebleria','panaderia','peluqueria','pizzeria','sandwicheria','spa','sushi','taller','verduleria','veterinaria'];
          var rubro = l.rubro||'';
          var valido = rubrosValidos.indexOf(rubro) >= 0;
          if(!valido && rubro && rubro !== 'otro'){
            return '<span style="font-size:11px;background:#fff3cd;color:#856404;padding:2px 8px;border-radius:10px;cursor:pointer" onclick="corregirRubro('+l.id+',\\''+rubro+'\\')">⚠ '+rubro+'</span>';
          }
          return '<span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">'+rubro+'</span>';
        })()}
      </td>"""

if old_rubro_td in content:
    content = content.replace(old_rubro_td, new_rubro_td)
    print("Badge rubro OK")
else:
    print("No encontrado badge")

# 2. Agregar modal para corregir rubro
old_modal_marker = '<!-- ─── LEADS'
new_modal = '''<!-- Modal Corregir Rubro -->
<div class="modal-overlay" id="modalCorregirRubro">
  <div class="modal" style="max-width:440px">
    <div class="modal-title">Corregir rubro del lead</div>
    <input type="hidden" id="corregirLeadId">
    <div style="background:#fff3cd;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:12px;color:#856404">
      ⚠ Rubro no reconocido: <strong id="corregirRubroActual"></strong>
    </div>
    <div class="form-row">
      <label class="form-lbl">Asignar rubro correcto</label>
      <select class="form-input" id="corregirRubroNuevo" onchange="onCorregirRubroChange(this.value)">
        <option value="">Selecciona rubro...</option>
        <option value="almacen">Almacen</option>
        <option value="bazar">Bazar</option>
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
      <input class="form-input" id="corregirCategoria" readonly style="background:#f8f9fa" placeholder="Se completa automaticamente">
    </div>
    <div style="font-size:11px;color:var(--mp-text-3);margin-top:4px">
      La imagen que se usara en el mensaje sera la de la categoria asignada
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalCorregirRubro')">Cancelar</button>
      <button class="btn btn-primary" onclick="guardarCorreccionRubro()">Guardar</button>
    </div>
  </div>
</div>

<!-- ─── LEADS'''

if '<!-- ─── LEADS' in content:
    content = content.replace(old_modal_marker, new_modal)
    print("Modal corregir OK")

# 3. Agregar JS para corregir rubro
js_fn = """
var RUBRO_CAT = {
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

function corregirRubro(leadId, rubroActual){
  document.getElementById('corregirLeadId').value = leadId;
  document.getElementById('corregirRubroActual').textContent = rubroActual;
  document.getElementById('corregirRubroNuevo').value = '';
  document.getElementById('corregirCategoria').value = '';
  document.getElementById('modalCorregirRubro').classList.add('open');
}

function onCorregirRubroChange(rubro){
  var cat = RUBRO_CAT[rubro] || '';
  document.getElementById('corregirCategoria').value = cat;
}

async function guardarCorreccionRubro(){
  var leadId = document.getElementById('corregirLeadId').value;
  var rubro = document.getElementById('corregirRubroNuevo').value;
  var categoria = document.getElementById('corregirCategoria').value;
  if(!rubro){ toast('Selecciona un rubro','error'); return; }
  var r = await api('/api/leads/'+leadId+'/update-rubro', {
    method:'PUT',
    body: JSON.stringify({rubro:rubro, categoria:categoria})
  });
  if(r&&r.ok){
    toast('Rubro actualizado correctamente','success');
    closeModal('modalCorregirRubro');
    loadLeads();
  } else toast('Error actualizando rubro','error');
}

"""

if 'function corregirRubro' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS corregirRubro OK")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")