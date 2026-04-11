with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Reemplazar el modal de status actual con uno que pida datos extra al cerrar
old_modal = '''<div class="modal-overlay" id="modalStatus">
  <div class="modal">
    <div class="modal-title">Cambiar estado del lead</div>
    <input type="hidden" id="statusLeadId">
    <div class="form-row">
      <label class="form-lbl">Nuevo estado</label>
      <select class="form-input" id="newStatus">
        <option value="enviado">Enviado</option>
        <option value="abierto">Abierto</option>
        <option value="interesado">Interesado ✅</option>
        <option value="quiere_reunion">Quiere reunión 📅</option>
        <option value="cerrado">Cerrado 🎉</option>
        <option value="no_interesado">No interesado ❌</option>
        <option value="opt_out">Opt-out 🚫</option>
      </select>
    </div>
    <div class="form-row">
      <label class="form-lbl">Notas (opcional)</label>
      <input class="form-input" id="statusNotes" placeholder="Ej: Llamó interesado, cotizar Point Pro">
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal(\'modalStatus\')">Cancelar</button>
      <button class="btn btn-primary" onclick="submitStatus()">Guardar</button>
    </div>
  </div>
</div>'''

new_modal = '''<div class="modal-overlay" id="modalStatus">
  <div class="modal">
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
    <!-- Campos extra solo para estado CERRADO -->
    <div id="camposCerrado" style="display:none;border-top:1px solid var(--mp-border);margin-top:12px;padding-top:12px">
      <div style="background:#d4edda;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:12px;color:#155724;font-weight:600">
        Completar datos del seller adquirido
      </div>
      <div class="form-row">
        <label class="form-lbl">Nombre de contacto <span style="color:var(--mp-red)">*</span></label>
        <input class="form-input" id="cerradoContacto" placeholder="Ej: Carlos Rojas (obligatorio)">
      </div>
      <div class="form-row">
        <label class="form-lbl">POS asignado <span style="color:var(--mp-red)">*</span></label>
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
        <input class="form-input" id="cerradoEmail" placeholder="contacto@negocio.cl" type="email">
      </div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal(\'modalStatus\')">Cancelar</button>
      <button class="btn btn-primary" onclick="submitStatus()">Guardar</button>
    </div>
  </div>
</div>'''

content = content.replace(old_modal, new_modal)
print('Modal actualizado:', 'camposCerrado' in content)

# Actualizar JS - onStatusChange y submitStatus
old_submit = '''async function submitStatus(){
  const id     = document.getElementById(\'statusLeadId\').value;
  const status = document.getElementById(\'newStatus\').value;
  const notes  = document.getElementById(\'statusNotes\').value;
  const r = await api(`/api/leads/${id}/status`, {
    method:\'PUT\', body:JSON.stringify({status, notes})
  });
  if(r?.ok){ toast(\'Estado actualizado\',\'success\'); closeModal(\'modalStatus\'); loadLeads(); }
  else toast(\'Error actualizando estado\',\'error\');
}'''

new_submit = '''function onStatusChange(status){
  const campos = document.getElementById('camposCerrado');
  if(status === 'cerrado'){
    campos.style.display = 'block';
    document.getElementById('modalStatusTitle').textContent = 'Registrar cierre de venta';
  } else {
    campos.style.display = 'none';
    document.getElementById('modalStatusTitle').textContent = 'Cambiar estado del lead';
  }
}

async function submitStatus(){
  const id     = document.getElementById('statusLeadId').value;
  const status = document.getElementById('newStatus').value;
  const notes  = document.getElementById('statusNotes').value;

  // Validacion para estado cerrado
  if(status === 'cerrado'){
    const contacto = document.getElementById('cerradoContacto').value.trim();
    if(!contacto){
      toast('El nombre de contacto es obligatorio para registrar un cierre','error');
      document.getElementById('cerradoContacto').focus();
      return;
    }
    const pos   = document.getElementById('cerradoPOS').value;
    const email = document.getElementById('cerradoEmail').value.trim();
    const notaFinal = `Contacto: ${contacto} | POS: ${pos}${email?' | Email: '+email:''}.${notes?' '+notes:''}`;

    const r = await api(`/api/leads/${id}/status`, {
      method:'PUT',
      body: JSON.stringify({
        status,
        notes: notaFinal,
        contact_name: contacto,
        pos_type: pos,
        email: email
      })
    });
    if(r?.ok){
      toast('Cierre registrado. Seller agregado automaticamente','success');
      closeModal('modalStatus');
      loadLeads();
    } else {
      toast('Error registrando cierre','error');
    }
    return;
  }

  const r = await api(`/api/leads/${id}/status`, {
    method:'PUT', body:JSON.stringify({status, notes})
  });
  if(r?.ok){ toast('Estado actualizado','success'); closeModal('modalStatus'); loadLeads(); }
  else toast('Error actualizando estado','error');
}'''

content = content.replace(old_submit, new_submit)
print('JS actualizado:', 'cerradoContacto' in content)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - modal cerrado actualizado')