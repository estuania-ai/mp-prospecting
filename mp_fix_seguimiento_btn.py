"""
mp_fix_seguimiento_btn.py
Agrega boton de seguimiento manual en tabla de leads
Solo aparece en leads con estado 'enviado'
"""
with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar boton seguimiento en acciones de cada lead
old_btns = '''          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},\'${l.status||\'no_enviado\'}\')">✏️</button>
          <button class="btn btn-ghost btn-sm" onclick="openWA(\'${l.phone}\')" title="WhatsApp">💬</button>'''

new_btns = '''          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},\'${l.status||\'no_enviado\'}\')">✏️</button>
          <button class="btn btn-ghost btn-sm" onclick="openWA(\'${l.phone}\')" title="WhatsApp">💬</button>
          ${(l.status==='enviado') ? \'<button class="btn btn-ghost btn-sm" onclick="sendSeguimiento(\'+ l.id +\',\'+ JSON.stringify(l.name) +\')" title="Enviar seguimiento" style="color:#856404">🔔</button>\' : \'\'}'''

content = content.replace(old_btns, new_btns)
print("Boton seguimiento OK:", '🔔' in content)

# 2. Agregar funcion sendSeguimiento al JS
new_fn = '''
async function sendSeguimiento(leadId, nombre){
  if(!confirm('Enviar mensaje de seguimiento a ' + nombre + '?')) return;
  toast('Enviando seguimiento...');
  const r = await api('/api/leads/'+leadId+'/seguimiento', {method:'POST'});
  if(r?.ok){
    toast('Seguimiento enviado a ' + nombre, 'success');
  } else {
    toast(r?.error || 'Error enviando seguimiento', 'error');
  }
}

'''

content = content.replace(
    'async function loadIntel(){',
    new_fn + 'async function loadIntel(){'
)
print("Funcion sendSeguimiento OK:", 'sendSeguimiento' in content)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
