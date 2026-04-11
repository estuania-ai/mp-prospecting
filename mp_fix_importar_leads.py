with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar boton Importar en header de leads
old_btn = '<button class="btn btn-ghost btn-sm" onclick="exportLeads()">⬇ Exportar CSV</button>'
new_btn = '<button class="btn btn-ghost btn-sm" onclick="exportLeads()">⬇ Exportar CSV</button>\n          <button class="btn btn-ghost btn-sm" onclick="document.getElementById(\'importFile\').click()">⬆ Importar</button>\n          <input type="file" id="importFile" accept=".xlsx" style="display:none" onchange="importarLeads(this)">'

if old_btn in content:
    content = content.replace(old_btn, new_btn)
    print("Boton importar OK")
else:
    # Buscar alternativa
    idx = content.find('exportLeads()')
    print("exportLeads pos:", idx)
    print("Contexto:", repr(content[idx-50:idx+100]))

# 2. Agregar funcion importarLeads JS
js_fn = """
function importarLeads(input){
  var file = input.files[0];
  if(!file){ return; }
  toast('Procesando archivo...', '');

  var reader = new FileReader();
  reader.onload = function(e){
    var data = new Uint8Array(e.target.result);
    var workbook = XLSX.read(data, {type:'array'});
    var sheet = workbook.Sheets[workbook.SheetNames[0]];
    var rows = XLSX.utils.sheet_to_json(sheet, {header:1});

    if(rows.length < 2){
      toast('El archivo esta vacio', 'error');
      return;
    }

    // Detectar columnas por nombre
    var headers = rows[0].map(function(h){ return (h||'').toString().toLowerCase().trim(); });
    var colNegocio  = headers.findIndex(function(h){ return h.includes('negocio') || h.includes('nombre'); });
    var colTelefono = headers.findIndex(function(h){ return h.includes('telefono') || h.includes('tel') || h.includes('phone'); });
    var colComuna   = headers.findIndex(function(h){ return h.includes('comuna'); });
    var colRubro    = headers.findIndex(function(h){ return h.includes('rubro'); });

    if(colNegocio===-1 || colTelefono===-1 || colComuna===-1 || colRubro===-1){
      toast('El archivo debe tener columnas: Negocio, Telefono, Comuna, Rubro', 'error');
      console.log('Headers encontrados:', headers);
      return;
    }

    var leads = [];
    for(var i=1; i<rows.length; i++){
      var row = rows[i];
      var negocio  = (row[colNegocio]||'').toString().trim();
      var telefono = (row[colTelefono]||'').toString().trim().replace(/\s/g,'');
      var comuna   = (row[colComuna]||'').toString().trim();
      var rubro    = (row[colRubro]||'').toString().trim().toLowerCase().replace(/ /g,'_');
      if(!negocio || !telefono) continue;
      leads.push({name:negocio, phone:telefono, comuna:comuna, rubro:rubro});
    }

    if(!leads.length){
      toast('No se encontraron leads validos', 'error');
      return;
    }

    // Enviar al servidor
    api('/api/leads/import', {
      method: 'POST',
      body: JSON.stringify({leads: leads})
    }).then(function(r){
      if(r && r.ok){
        toast('Importados: '+r.importados+' leads. Duplicados: '+r.duplicados, 'success');
        loadLeads();
      } else {
        toast('Error importando: '+(r&&r.error||'desconocido'), 'error');
      }
    });
  };
  reader.readAsArrayBuffer(file);
  input.value = '';
}

"""

if 'function importarLeads' not in content:
    content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
    print("JS importar OK")

# 3. Agregar SheetJS library en el head
if 'SheetJS' not in content and 'xlsx.full.min' not in content:
    content = content.replace(
        '</head>',
        '<script src="https://cdnjs.cloudflare.com/ajax/libs/xlsx/0.18.5/xlsx.full.min.js"></script>\n</head>'
    )
    print("SheetJS agregado OK")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")