with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},'${l.status||'enviado'}')">✏️</button>
          <a href="https://wa.me/${l.phone?.replace(/\\D/g,'')}" target="_blank" class="btn btn-green btn-sm">💬</a>
        </div>"""

new = """          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},'${l.status||'enviado'}')">✏️</button>
          <a href="https://wa.me/${l.phone?.replace(/\\D/g,'')}" target="_blank" class="btn btn-green btn-sm">💬</a>
          ${l.status==='enviado' ? `<button class="btn btn-ghost btn-sm" onclick="sendSeguimiento(${l.id},'${l.name.replace(/'/g,'')}')" title="Seguimiento 24h/72h" style="color:#856404">🔔</button>` : ''}
        </div>"""

if old in content:
    content = content.replace(old, new)
    print("Boton 🔔 agregado OK")
else:
    print("ERROR - texto no encontrado")

# 2. Agregar funcion JS sendSeguimiento
if 'function sendSeguimiento' not in content:
    js_fn = """
async function sendSeguimiento(leadId, nombre){
  if(!confirm('Enviar seguimiento a ' + nombre + '?')) return;
  toast('Enviando seguimiento...');
  const r = await api('/api/leads/'+leadId+'/seguimiento', {method:'POST'});
  if(r && r.ok){
    toast('Seguimiento enviado a ' + nombre + ' (' + (r.tipo||'') + ')', 'success');
    loadLeads();
  } else {
    toast((r && r.error) || 'Error enviando seguimiento', 'error');
  }
}

"""
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("Funcion JS OK")
else:
    print("Funcion JS ya existe")

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")