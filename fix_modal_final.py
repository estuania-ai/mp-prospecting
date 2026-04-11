with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Encontrar y reemplazar el modal completo
start = content.find('<div class="modal-overlay" id="modalStatus">')
end = content.find('</div>\n\n<div class="toast"', start) + 6
print('Modal desde:', start, 'hasta:', end)
print('Texto actual:', content[start:start+100])

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
      <input class="form-input" id="statusNotes" placeholder="Ej: Cliente interesado en Point Pro">
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
      <button class="btn btn-primary" id="btnGuardarStatus" onclick="submitStatus()">Guardar</button>
    </div>
  </div>
</div>'''

content = content[:start] + new_modal + content[end:]
print('Nuevo modal insertado OK')

# Reemplazar funciones JS
old_fn = content.find('function onStatusChange')
if old_fn > 0:
    end_fn = content.find('\nasync function submitStatus', old_fn)
    content = content[:old_fn] + content[end_fn+1:]
    print('Funcion onStatusChange vieja removida')

old_submit = content.find('async function submitStatus()')
end_submit = content.find('\nfunction exportLeads', old_submit)
print('submitStatus desde:', old_submit, 'hasta:', end_submit)

new_fns = '''function onStatusChange(status){
  const c = document.getElementById('camposCerrado');
  const t = document.getElementById('modalStatusTitle');
  if(status === 'cerrado'){
    c.style.display = 'block';
    t.textContent = 'Registrar cierre de venta';
  } else {
    c.style.display = 'none';
    t.textContent = 'Cambiar estado del lead';
  }
}

async function submitStatus(){
  const id     = document.getElementById('statusLeadId').value;
  const status = document.getElementById('newStatus').value;
  const notes  = document.getElementById('statusNotes').value;

  if(status === 'cerrado'){
    const contacto = document.getElementById('cerradoContacto').value.trim();
    if(!contacto){
      document.getElementById('cerradoContacto').style.border = '2px solid red';
      toast('El nombre de contacto es obligatorio','error');
      return;
    }
    const pos   = document.getElementById('cerradoPOS').value;
    const email = document.getElementById('cerradoEmail').value.trim();
    const r = await api('/api/leads/'+id+'/status', {
      method:'PUT',
      body: JSON.stringify({status, notes, contact_name:contacto, pos_type:pos, email:email})
    });
    if(r?.ok){
      toast('Cierre registrado. Seller agregado automaticamente','success');
      closeModal('modalStatus');
      loadLeads();
    } else {
      toast('Error: '+(r?.error||'desconocido'),'error');
    }
    return;
  }

  const r = await api('/api/leads/'+id+'/status', {
    method:'PUT', body:JSON.stringify({status, notes})
  });
  if(r?.ok){ toast('Estado actualizado','success'); closeModal('modalStatus'); loadLeads(); }
  else toast('Error actualizando estado','error');
}

'''

content = content[:old_submit] + new_fns + content[end_submit+1:]
print('Funciones JS actualizadas')

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - modal y JS reemplazados')