"""
mp_fix_import_mejoras.py
1. Reconocimiento fuzzy de rubros (tildes, mayusculas, errores tipograficos)
2. Anular importacion con boton
Trabaja sobre dashboard_test8.html
"""
with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Mejorar reconocimiento de rubros en importarLeads
old_rubro = "      var rubro    = (row[colRubro]||'').toString().trim().toLowerCase().replace(/ /g,'_');"

new_rubro = """      var rubroRaw = (row[colRubro]||'').toString().trim();
      var rubro = normalizarRubro(rubroRaw);"""

if old_rubro in content:
    content = content.replace(old_rubro, new_rubro)
    print("Rubro raw OK")
else:
    print("No encontrado rubro raw")
    idx = content.find('colRubro')
    print("Contexto:", repr(content[idx:idx+150]))

# 2. Agregar funcion normalizarRubro y trackeo de importacion
js_fn = """
function normalizarRubro(raw){
  var s = raw.toLowerCase()
    .replace(/á/g,'a').replace(/é/g,'e').replace(/í/g,'i').replace(/ó/g,'o').replace(/ú/g,'u')
    .replace(/ü/g,'u').replace(/ñ/g,'n')
    .replace(/[^a-z0-9]/g,'_').replace(/_+/g,'_').replace(/^_|_$/g,'');

  var mapa = {
    'botilleria':'botilleria','botillería':'botilleria','botillera':'botilleria',
    'carniceria':'carniceria','carnicería':'carniceria',
    'almacen':'almacen','almacén':'almacen','almacen_de_barrio':'almacen',
    'cafeteria':'cafeteria','cafetería':'cafeteria','cafe':'cafeteria',
    'panaderia':'panaderia','panadería':'panaderia',
    'fruteria':'fruteria','frutería':'fruteria','verduleria':'verduleria','verdulería':'verduleria',
    'minimarket':'minimarket','mini_market':'minimarket',
    'farmacia':'farmacia','ferreteria':'ferreteria','ferretería':'ferreteria',
    'peluqueria':'peluqueria','peluquería':'peluqueria','barberia':'peluqueria','barbería':'peluqueria',
    'lavanderia':'lavanderia','lavandería':'lavanderia',
    'pizzeria':'pizzeria','pizzería':'pizzeria',
    'sushi':'sushi','sandwicheria':'sandwicheria','sandwichería':'sandwicheria',
    'fuente_de_soda':'fuente_de_soda','fuente_soda':'fuente_de_soda',
    'cafeteria_fuente':'cafeteria',
    'gimnasio':'gimnasio','gym':'gimnasio',
    'spa':'spa','estetica':'spa','estética':'spa',
    'clinica_dental':'clinica_dental','clinica':'clinica_dental','dental':'clinica_dental',
    'veterinaria':'veterinaria','vet':'veterinaria',
    'taller':'taller','taller_mecanico':'taller','mecanico':'taller',
    'libreria':'libreria','librería':'libreria',
    'muebleria':'muebleria','mueblería':'muebleria',
    'bazar':'bazar','emporio':'emporio'
  };

  // Buscar match exacto primero
  if(mapa[s]) return mapa[s];

  // Buscar match parcial
  var rubrosValidos = ['almacen','bazar','botilleria','cafeteria','carniceria','clinica_dental',
    'emporio','farmacia','ferreteria','fruteria','fuente_de_soda','gimnasio','lavanderia',
    'libreria','minimarket','muebleria','panaderia','peluqueria','pizzeria','sandwicheria',
    'spa','sushi','taller','verduleria','veterinaria'];

  for(var i=0; i<rubrosValidos.length; i++){
    if(s.includes(rubrosValidos[i]) || rubrosValidos[i].includes(s)){
      return rubrosValidos[i];
    }
  }

  return s || 'otro';
}

var ultimaImportacion = [];

function marcarImportacion(ids){
  ultimaImportacion = ids;
  var btn = document.getElementById('btnAnularImport');
  if(btn && ids.length > 0){
    btn.style.display = 'inline-block';
    btn.textContent = '↩ Anular importacion (' + ids.length + ')';
  }
}

async function anularImportacion(){
  if(!ultimaImportacion.length){ toast('No hay importacion reciente para anular','error'); return; }
  if(!confirm('Anular importacion de ' + ultimaImportacion.length + ' leads?')) return;
  var r = await api('/api/leads/anular-importacion', {
    method:'POST',
    body: JSON.stringify({ids: ultimaImportacion})
  });
  if(r&&r.ok){
    toast('Importacion anulada: '+r.eliminados+' leads eliminados','success');
    ultimaImportacion = [];
    document.getElementById('btnAnularImport').style.display='none';
    loadLeads();
  } else toast('Error anulando','error');
}

"""

if 'function normalizarRubro' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS normalizarRubro OK")

# 3. Agregar boton Anular en header leads
old_importar_btn = '<button class="btn btn-ghost btn-sm" onclick="document.getElementById(\'importFile\').click()">⬆ Importar</button>'
new_importar_btn = '<button class="btn btn-ghost btn-sm" onclick="document.getElementById(\'importFile\').click()">⬆ Importar</button>\n          <button id="btnAnularImport" class="btn btn-ghost btn-sm" onclick="anularImportacion()" style="display:none;color:var(--mp-red)">↩ Anular importacion</button>'

if old_importar_btn in content:
    content = content.replace(old_importar_btn, new_importar_btn)
    print("Boton anular OK")

# 4. Actualizar importarLeads para trackear ids y llamar marcarImportacion
old_toast = "    toast('Importando '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');"
new_toast = """    toast('Importados: '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');
        if(r.ids) marcarImportacion(r.ids);"""

if old_toast in content:
    content = content.replace(old_toast, new_toast)
    print("Track importacion OK")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
