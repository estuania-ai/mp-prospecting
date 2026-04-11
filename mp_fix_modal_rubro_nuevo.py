with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar modal corregir rubro con version mejorada
old_modal = '''<!-- Modal Corregir Rubro -->
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
</div>'''

new_modal = '''<!-- Modal Corregir Rubro -->
<div class="modal-overlay" id="modalCorregirRubro">
  <div class="modal" style="max-width:460px">
    <div class="modal-title">Rubro no reconocido</div>
    <input type="hidden" id="corregirLeadId">
    <input type="hidden" id="corregirRubroOriginal">

    <div style="background:#fff3cd;border-radius:8px;padding:10px 14px;margin-bottom:14px;font-size:12px;color:#856404">
      ⚠ Rubro importado: <strong id="corregirRubroActual"></strong>
    </div>

    <!-- Pregunta agregar nuevo -->
    <div id="seccionPregunta">
      <div style="font-size:13px;font-weight:600;color:var(--mp-text-1);margin-bottom:12px">
        ¿Que deseas hacer con este rubro?
      </div>
      <div style="display:flex;flex-direction:column;gap:8px">
        <button onclick="mostrarSeccion('asignar')" style="background:#e8f4fd;border:1px solid #bee3f8;border-radius:8px;padding:12px;text-align:left;cursor:pointer;font-size:12px">
          <div style="font-weight:700;color:var(--mp-blue)">📋 Asignar a un rubro existente</div>
          <div style="color:var(--mp-text-3);margin-top:2px">Selecciona el rubro mas similar de nuestra lista</div>
        </button>
        <button onclick="mostrarSeccion('nuevo')" style="background:#f0fff4;border:1px solid #c6f6d5;border-radius:8px;padding:12px;text-align:left;cursor:pointer;font-size:12px">
          <div style="font-weight:700;color:#276749">✨ Agregar como nuevo rubro</div>
          <div style="color:var(--mp-text-3);margin-top:2px">Mantener el nombre del rubro y asignarle una categoria</div>
        </button>
      </div>
    </div>

    <!-- Seccion asignar existente -->
    <div id="seccionAsignar" style="display:none">
      <button onclick="mostrarSeccion('pregunta')" style="background:none;border:none;color:var(--mp-blue);cursor:pointer;font-size:12px;padding:0;margin-bottom:12px">← Volver</button>
      <div class="form-row">
        <label class="form-lbl">Selecciona rubro correcto</label>
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
      <div style="font-size:11px;color:var(--mp-text-3)">La imagen del mensaje correspondera a esta categoria</div>
    </div>

    <!-- Seccion nuevo rubro -->
    <div id="seccionNuevo" style="display:none">
      <button onclick="mostrarSeccion('pregunta')" style="background:none;border:none;color:var(--mp-blue);cursor:pointer;font-size:12px;padding:0;margin-bottom:12px">← Volver</button>
      <div class="form-row">
        <label class="form-lbl">Nombre del nuevo rubro</label>
        <input class="form-input" id="nuevoRubroNombre" placeholder="Ej: uniformes_escolares">
      </div>
      <div class="form-row">
        <label class="form-lbl">Categoria <span style="color:red">*</span></label>
        <select class="form-input" id="nuevoRubroCategoria">
          <option value="">Selecciona categoria...</option>
          <option value="Comercio de Alta Demanda Fin de Semana">Comercio de Alta Demanda Fin de Semana</option>
          <option value="Comercio de Barrio Diario">Comercio de Barrio Diario</option>
          <option value="Gastronomia y Comida Rapida">Gastronomia y Comida Rapida</option>
          <option value="Membresias y Entrenamientos">Membresias y Entrenamientos</option>
          <option value="Retail Especializado y Hogar">Retail Especializado y Hogar</option>
          <option value="Salud y Farmacia">Salud y Farmacia</option>
          <option value="Servicios de Alto Ticket">Servicios de Alto Ticket</option>
          <option value="Servicios Personales Diario">Servicios Personales Diario</option>
        </select>
      </div>
      <div style="background:#f0fff4;border-radius:8px;padding:8px 12px;font-size:11px;color:#276749;margin-top:4px">
        ✓ Se usara el mensaje universal y la imagen de la categoria seleccionada
      </div>
    </div>

    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalCorregirRubro')">Cancelar</button>
      <button class="btn btn-primary" id="btnGuardarRubro" onclick="guardarCorreccionRubro()" style="display:none">Guardar</button>
    </div>
  </div>
</div>'''

if old_modal in content:
    content = content.replace(old_modal, new_modal)
    print("Modal actualizado OK")
else:
    print("No encontrado - buscando...")
    idx = content.find('modalCorregirRubro')
    print("pos:", idx)

# Actualizar JS
old_js = """function mostrarSeccion"""
if 'function mostrarSeccion' not in content:
    js_add = """
function mostrarSeccion(seccion){
  document.getElementById('seccionPregunta').style.display = seccion==='pregunta'?'block':'none';
  document.getElementById('seccionAsignar').style.display = seccion==='asignar'?'block':'none';
  document.getElementById('seccionNuevo').style.display = seccion==='nuevo'?'block':'none';
  document.getElementById('btnGuardarRubro').style.display = (seccion==='asignar'||seccion==='nuevo')?'inline-block':'none';
  if(seccion==='nuevo'){
    document.getElementById('nuevoRubroNombre').value = document.getElementById('corregirRubroOriginal').value;
  }
}

"""
    content = content.replace('function corregirRubro(', js_add + 'function corregirRubro(')
    print("JS mostrarSeccion OK")

# Update corregirRubro function
old_corregir = """function corregirRubro(leadId, rubroActual){
  document.getElementById('corregirLeadId').value = leadId;
  document.getElementById('corregirRubroActual').textContent = rubroActual;
  document.getElementById('corregirRubroNuevo').value = '';
  document.getElementById('corregirCategoria').value = '';
  document.getElementById('modalCorregirRubro').classList.add('open');
}"""

new_corregir = """function corregirRubro(leadId, rubroActual){
  document.getElementById('corregirLeadId').value = leadId;
  document.getElementById('corregirRubroActual').textContent = rubroActual;
  document.getElementById('corregirRubroOriginal').value = rubroActual;
  document.getElementById('corregirRubroNuevo').value = '';
  document.getElementById('corregirCategoria').value = '';
  mostrarSeccion('pregunta');
  document.getElementById('modalCorregirRubro').classList.add('open');
}"""

if old_corregir in content:
    content = content.replace(old_corregir, new_corregir)
    print("corregirRubro actualizado OK")

# Update guardarCorreccionRubro
old_guardar = """async function guardarCorreccionRubro(){
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
}"""

new_guardar = """async function guardarCorreccionRubro(){
  var leadId = document.getElementById('corregirLeadId').value;
  var seccionActiva = document.getElementById('seccionAsignar').style.display !== 'none' ? 'asignar' : 'nuevo';
  var rubro, categoria;

  if(seccionActiva === 'asignar'){
    rubro = document.getElementById('corregirRubroNuevo').value;
    categoria = document.getElementById('corregirCategoria').value;
    if(!rubro){ toast('Selecciona un rubro','error'); return; }
  } else {
    rubro = document.getElementById('nuevoRubroNombre').value.trim().toLowerCase().replace(/ /g,'_');
    categoria = document.getElementById('nuevoRubroCategoria').value;
    if(!rubro){ toast('Ingresa el nombre del rubro','error'); return; }
    if(!categoria){ toast('Selecciona una categoria','error'); return; }
  }

  var r = await api('/api/leads/'+leadId+'/update-rubro', {
    method:'PUT',
    body: JSON.stringify({rubro:rubro, categoria:categoria})
  });
  if(r&&r.ok){
    toast('Rubro actualizado correctamente','success');
    closeModal('modalCorregirRubro');
    loadLeads();
  } else toast('Error actualizando rubro','error');
}"""

if old_guardar in content:
    content = content.replace(old_guardar, new_guardar)
    print("guardarCorreccionRubro OK")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")