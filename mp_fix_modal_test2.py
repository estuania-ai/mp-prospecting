with open('templates/dashboard_test2.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar llamada a onStatusChange en openStatusModal
old = """function openStatusModal(id, currentStatus){
  document.getElementById('statusLeadId').value = id;
  document.getElementById('newStatus').value = currentStatus;
  document.getElementById('statusNotes').value = '';
  document.getElementById('modalStatus').classList.add('open');
}"""

new = """function openStatusModal(id, currentStatus){
  document.getElementById('statusLeadId').value = id;
  document.getElementById('newStatus').value = currentStatus;
  document.getElementById('statusNotes').value = '';
  // Resetear campos extra
  if(document.getElementById('cerradoContacto')) document.getElementById('cerradoContacto').value = '';
  if(document.getElementById('cerradoContacto')) document.getElementById('cerradoContacto').style.border = '';
  if(document.getElementById('optoutMotivo')) document.getElementById('optoutMotivo').value = '';
  if(document.getElementById('optoutMotivo')) document.getElementById('optoutMotivo').style.border = '';
  if(document.getElementById('optoutNota')) document.getElementById('optoutNota').value = '';
  // Mostrar campos segun estado actual
  if(typeof onStatusChange === 'function') onStatusChange(currentStatus);
  document.getElementById('modalStatus').classList.add('open');
}"""

if old in content:
    content = content.replace(old, new)
    print("openStatusModal OK")
else:
    print("No encontrado - buscando...")
    idx = content.find('function openStatusModal')
    print(content[idx:idx+300])

# 2. Agregar modal completo con campos si no existe
if 'camposOptout' not in content:
    print("Agregando modal completo...")
    # Reemplazar modal basico
    old_modal_start = '<div class="modal-overlay" id="modalStatus">'
    idx_modal = content.find(old_modal_start)
    idx_end = content.find('</div>\n\n<!--', idx_modal)
    if idx_end == -1:
        idx_end = content.find('\n\n<!-- ', idx_modal)

    new_modal = '''<div class="modal-overlay" id="modalStatus">
  <div class="modal" style="max-width:500px">
    <div class="modal-title" id="modalStatusTitle">Cambiar estado del lead</div>
    <input type="hidden" id="statusLeadId">
    <div class="form-row">
      <label class="form-lbl">Nuevo estado</label>
      <select class="form-input" id="newStatus" onchange="onStatusChange(this.value)">
        <option value="no_enviado">No enviado</option>
        <option value="enviado">Enviado</option>
        <option value="abierto">Abierto</option>
        <option value="interesado">Interesado</option>
        <option value="quiere_reunion">Quiere reunion</option>
        <option value="cerrado">Cerrado</option>
        <option value="no_interesado">No interesado</option>
        <option value="opt_out">Opt-out</option>
      </select>
    </div>
    <div class="form-row">
      <label class="form-lbl">Notas (opcional)</label>
      <input class="form-input" id="statusNotes" placeholder="Observaciones adicionales">
    </div>
    <div id="camposOptout" style="display:none;border-top:1px solid #dde5ef;margin-top:12px;padding-top:12px">
      <div style="background:#f8d7da;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:12px;color:#721c24;font-weight:600">
        Registrar motivo
      </div>
      <div class="form-row">
        <label class="form-lbl">Motivo <span style="color:red">*</span></label>
        <select class="form-input" id="optoutMotivo">
          <option value="">Selecciona motivo...</option>
          <option value="Sin interes">Sin interes</option>
          <option value="Sin respuesta">Sin respuesta</option>
          <option value="Tiene MP">Ya tiene Mercado Pago</option>
          <option value="Precio">Precio no conveniente</option>
          <option value="Otro">Otro</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-lbl">Nota adicional (opcional)</label>
        <input class="form-input" id="optoutNota" placeholder="Ej: Tiene contrato vigente">
      </div>
    </div>
    <div id="camposCerrado" style="display:none;border-top:1px solid #dde5ef;margin-top:12px;padding-top:12px">
      <div style="background:#d4edda;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:12px;color:#155724;font-weight:600">
        Completar datos del seller adquirido
      </div>
      <div class="form-row">
        <label class="form-lbl">Nombre de contacto <span style="color:red">*</span></label>
        <input class="form-input" id="cerradoContacto" placeholder="Ej: Carlos Rojas (obligatorio)">
      </div>
      <div class="form-row">
        <label class="form-lbl">POS asignado</label>
        <select class="form-input" id="cerradoPOS">
          <option value="Point Pro 2" selected>Point Pro 2</option>
          <option value="Point Smart 2">Point Smart 2</option>
          <option value="Point Air">Point Air</option>
          <option value="Point Mini">Point Mini</option>
          <option value="Point Plus">Point Plus</option>
        </select>
      </div>
      <div class="form-row">
        <label class="form-lbl">Email (opcional)</label>
        <input class="form-input" id="cerradoEmail" placeholder="contacto@negocio.cl">
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalStatus')">Cancelar</button>
      <button class="btn btn-primary" onclick="submitStatus()">Guardar</button>
    </div>
  </div>
</div>'''

    content = content[:idx_modal] + new_modal + content[idx_end:]
    print("Modal completo agregado")

# 3. Agregar funciones JS si no existen
if 'function onStatusChange' not in content:
    js = '''
function onStatusChange(status){
  var cc = document.getElementById('camposCerrado');
  var co = document.getElementById('camposOptout');
  var t  = document.getElementById('modalStatusTitle');
  if(cc) cc.style.display = 'none';
  if(co) co.style.display = 'none';
  if(status === 'cerrado'){
    if(cc) cc.style.display = 'block';
    if(t) t.textContent = 'Registrar cierre de venta';
  } else if(status === 'opt_out' || status === 'no_interesado'){
    if(co) co.style.display = 'block';
    if(t) t.textContent = status === 'opt_out' ? 'Registrar Opt-out' : 'Registrar No interesado';
  } else {
    if(t) t.textContent = 'Cambiar estado del lead';
  }
}

async function submitStatus(){
  var id     = document.getElementById('statusLeadId').value;
  var status = document.getElementById('newStatus').value;
  var notes  = document.getElementById('statusNotes').value;
  if(status === 'opt_out' || status === 'no_interesado'){
    var motivo = document.getElementById('optoutMotivo').value;
    if(!motivo){ document.getElementById('optoutMotivo').style.border='2px solid red'; toast('Selecciona un motivo','error'); return; }
    var nota = document.getElementById('optoutNota').value.trim();
    var r = await api('/api/leads/'+id+'/status',{method:'PUT',body:JSON.stringify({status:status,notes:motivo+(nota?' - '+nota:''),optout_motivo:motivo})});
    if(r&&r.ok){ toast('Registrado: '+motivo,'success'); closeModal('modalStatus'); loadLeads(); }
    else toast('Error','error');
    return;
  }
  if(status === 'cerrado'){
    var contacto = document.getElementById('cerradoContacto').value.trim();
    if(!contacto){ document.getElementById('cerradoContacto').style.border='2px solid red'; toast('Nombre de contacto obligatorio','error'); return; }
    var pos = document.getElementById('cerradoPOS').value;
    var email = document.getElementById('cerradoEmail').value.trim();
    var r = await api('/api/leads/'+id+'/status',{method:'PUT',body:JSON.stringify({status:status,notes:notes,contact_name:contacto,pos_type:pos,email:email})});
    if(r&&r.ok){ toast('Cierre registrado. Seller agregado','success'); closeModal('modalStatus'); loadLeads(); }
    else toast('Error: '+(r&&r.error?r.error:'desconocido'),'error');
    return;
  }
  var r = await api('/api/leads/'+id+'/status',{method:'PUT',body:JSON.stringify({status:status,notes:notes})});
  if(r&&r.ok){ toast('Estado actualizado','success'); closeModal('modalStatus'); loadLeads(); }
  else toast('Error actualizando estado','error');
}

'''
    content = content.replace('function openStatusModal', js + 'function openStatusModal')
    print("JS funciones agregadas OK")

with open('templates/dashboard_test2.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("camposOptout:", 'camposOptout' in content)
print("onStatusChange:", 'function onStatusChange' in content)
print("submitStatus:", 'async function submitStatus' in content)
print("LISTO")