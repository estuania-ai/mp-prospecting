with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar campos extra para opt-out en el modal
old_campos = '''    <div id="camposCerrado" style="display:none;border-top:1px solid #dde5ef;margin-top:12px;padding-top:12px">'''

new_campos = '''    <div id="camposOptout" style="display:none;border-top:1px solid #dde5ef;margin-top:12px;padding-top:12px">
      <div style="background:#f8d7da;border-radius:8px;padding:8px 12px;margin-bottom:12px;font-size:12px;color:#721c24;font-weight:600">
        Registrar motivo de Opt-out
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
        <input class="form-input" id="optoutNota" placeholder="Ej: Cliente tiene contrato vigente con otro proveedor">
      </div>
    </div>

    <div id="camposCerrado" style="display:none;border-top:1px solid #dde5ef;margin-top:12px;padding-top:12px">'''

content = content.replace(old_campos, new_campos)
print("Campos optout OK:", 'camposOptout' in content)

# 2. Actualizar onStatusChange para mostrar campos optout
old_status_change = '''function onStatusChange(status){
  var c = document.getElementById('camposCerrado');
  var t = document.getElementById('modalStatusTitle');
  if(status === 'cerrado'){
    c.style.display = 'block';
    t.textContent = 'Registrar cierre de venta';
  } else {
    c.style.display = 'none';
    t.textContent = 'Cambiar estado del lead';
  }
}'''

new_status_change = '''function onStatusChange(status){
  var cc = document.getElementById('camposCerrado');
  var co = document.getElementById('camposOptout');
  var t  = document.getElementById('modalStatusTitle');
  cc.style.display = 'none';
  co.style.display = 'none';
  if(status === 'cerrado'){
    cc.style.display = 'block';
    t.textContent = 'Registrar cierre de venta';
  } else if(status === 'opt_out' || status === 'no_interesado'){
    co.style.display = 'block';
    t.textContent = status === 'opt_out' ? 'Registrar Opt-out' : 'Registrar No interesado';
  } else {
    t.textContent = 'Cambiar estado del lead';
  }
}'''

content = content.replace(old_status_change, new_status_change)
print("onStatusChange OK:", 'camposOptout' in content and 'opt_out' in content)

# 3. Actualizar submitStatus para incluir motivo optout
old_submit_start = '''  if(status === 'cerrado'){
    var contacto = document.getElementById('cerradoContacto').value.trim();'''

new_submit_start = '''  if(status === 'opt_out' || status === 'no_interesado'){
    var motivo = document.getElementById('optoutMotivo').value;
    if(!motivo){
      document.getElementById('optoutMotivo').style.border = '2px solid red';
      toast('Selecciona un motivo','error');
      return;
    }
    var nota = document.getElementById('optoutNota').value.trim();
    var notaFinal = motivo + (nota ? ' - ' + nota : '');
    var r = await api('/api/leads/'+id+'/status', {
      method:'PUT',
      body: JSON.stringify({status:status, notes:notaFinal, optout_motivo:motivo})
    });
    if(r && r.ok){
      toast('Estado registrado: ' + motivo,'success');
      closeModal('modalStatus');
      loadLeads();
    } else {
      toast('Error registrando estado','error');
    }
    return;
  }

  if(status === 'cerrado'){
    var contacto = document.getElementById('cerradoContacto').value.trim();'''

content = content.replace(old_submit_start, new_submit_start)
print("submitStatus optout OK:", 'optoutMotivo' in content)

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")