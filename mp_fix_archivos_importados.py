"""
mp_fix_archivos_importados.py
Agrega boton Archivos Importados con modal protegido por password
Trabaja sobre dashboard_test8.html
"""
with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar boton en header leads
old_btn = '<button id="btnAnularImport"'
new_btn = '<button class="btn btn-ghost btn-sm" onclick="abrirArchivosImportados()">📁 Archivos Importados</button>\n          <button id="btnAnularImport"'

if old_btn in content:
    content = content.replace(old_btn, new_btn)
    print("Boton archivos OK")
else:
    print("No encontrado btn anular")

# 2. Agregar modal archivos importados
modal_html = '''
<!-- Modal Archivos Importados -->
<div class="modal-overlay" id="modalArchivosImportados">
  <div class="modal" style="max-width:560px">
    <div class="modal-title">📁 Archivos Importados</div>
    <div id="archivosList" style="max-height:350px;overflow-y:auto;display:flex;flex-direction:column;gap:8px">
      <div style="text-align:center;padding:20px"><div class="spinner"></div></div>
    </div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalArchivosImportados')">Cerrar</button>
    </div>
  </div>
</div>

<!-- Modal Password Eliminar -->
<div class="modal-overlay" id="modalPasswordEliminar">
  <div class="modal" style="max-width:340px">
    <div class="modal-title">🔒 Confirmar eliminacion</div>
    <input type="hidden" id="eliminarImpId">
    <div style="font-size:12px;color:var(--mp-text-3);margin-bottom:12px">
      Esta accion eliminara todos los leads de esta importacion. Ingresa la contrasena para confirmar.
    </div>
    <div class="form-row">
      <label class="form-lbl">Contrasena</label>
      <input type="password" class="form-input" id="passwordEliminar" placeholder="••••••••" onkeydown="if(event.key==='Enter')confirmarEliminarImportacion()">
    </div>
    <div id="passwordError" style="color:var(--mp-red);font-size:11px;display:none">Contrasena incorrecta</div>
    <div class="modal-actions">
      <button class="btn btn-ghost" onclick="closeModal('modalPasswordEliminar')">Cancelar</button>
      <button class="btn btn-primary" onclick="confirmarEliminarImportacion()">Eliminar</button>
    </div>
  </div>
</div>

'''

if 'modalArchivosImportados' not in content:
    content = content.replace('<!-- ─── LEADS', modal_html + '<!-- ─── LEADS')
    print("Modal archivos OK")

# 3. Agregar JS
js_fn = """
async function abrirArchivosImportados(){
  document.getElementById('modalArchivosImportados').classList.add('open');
  var r = await api('/api/leads/importaciones');
  if(!r || !r.length){
    document.getElementById('archivosList').innerHTML = '<div style="text-align:center;color:var(--mp-text-3);padding:20px">Sin archivos importados</div>';
    return;
  }
  document.getElementById('archivosList').innerHTML = r.map(function(imp){
    return '<div style="background:#f8f9fa;border-radius:8px;padding:12px;border:1px solid var(--mp-border)">' +
      '<div style="display:flex;justify-content:space-between;align-items:center">' +
      '<div>' +
      '<div style="font-size:13px;font-weight:600;color:var(--mp-text-1)">📄 '+imp.filename+'</div>' +
      '<div style="font-size:11px;color:var(--mp-text-3);margin-top:2px">'+imp.created_at.substring(0,16)+' · '+imp.importados+' leads importados · '+imp.duplicados+' duplicados</div>' +
      '</div>' +
      '<button onclick="pedirPasswordEliminar('+imp.id+')" style="background:#fff5f5;color:var(--mp-red);border:1px solid #ffd0d0;border-radius:8px;padding:4px 12px;cursor:pointer;font-size:11px;font-weight:600">🗑 Eliminar</button>' +
      '</div></div>';
  }).join('');
}

function pedirPasswordEliminar(impId){
  document.getElementById('eliminarImpId').value = impId;
  document.getElementById('passwordEliminar').value = '';
  document.getElementById('passwordError').style.display = 'none';
  document.getElementById('modalPasswordEliminar').classList.add('open');
}

async function confirmarEliminarImportacion(){
  var pwd = document.getElementById('passwordEliminar').value;
  if(pwd !== 'Tefita01.'){
    document.getElementById('passwordError').style.display = 'block';
    return;
  }
  var impId = document.getElementById('eliminarImpId').value;
  var r = await api('/api/leads/importaciones/'+impId, {method:'DELETE'});
  if(r&&r.ok){
    toast('Importacion eliminada: '+r.eliminados+' leads removidos','success');
    closeModal('modalPasswordEliminar');
    abrirArchivosImportados();
    loadLeads();
  } else toast('Error eliminando','error');
}

"""

if 'function abrirArchivosImportados' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS archivos OK")

# 4. Agregar filename en importarLeads
old_api_call = "api('/api/leads/import', {\n      method: 'POST',\n      body: JSON.stringify({leads: leads})"
new_api_call = "api('/api/leads/import', {\n      method: 'POST',\n      body: JSON.stringify({leads: leads, filename: file.name})"

if old_api_call in content:
    content = content.replace(old_api_call, new_api_call)
    print("Filename en import OK")
else:
    print("filename - buscando alternativa...")
    idx = content.find("JSON.stringify({leads: leads")
    print("Contexto:", repr(content[idx:idx+80]))

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
