with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar antes
print("checkWaStatus antes:", 'function checkWaStatus' in content)
print("loadLeads antes:", 'function loadLeads' in content)

# 1. Agregar boton en header interesados
old = '<button class="btn btn-ghost" onclick="showModalNuevoProspecto()">+ Agregar Manual</button>'
new = '<button class="btn btn-ghost" onclick="showModalNuevoProspecto()">+ Agregar Manual</button>\n      <button class="btn btn-ghost" onclick="exportarInteresados()">⬇ Exportar</button>'

if old in content:
    content = content.replace(old, new)
    print("Boton exportar OK")
else:
    print("Boton no encontrado")

# 2. Agregar funcion JS ANTES del cierre del script - buscar setInterval
js_fn = """
function exportarInteresados(){
  api('/api/prospects/').then(function(prospects){
    if(!prospects||!prospects.length){toast('Sin interesados','error');return;}
    var h = ['ID','Nombre','Telefono','Negocio','Rubro','Categoria','Comuna','Competencia','Procedencia','Notas','Tiene Tareas','Tareas Pendientes','Creado','Actualizado'];
    var lines = [h.join(',')];
    prospects.forEach(function(p){
      var notas = (p.notas||'').replace(/,/g,';').replace(/\\n/g,' ');
      lines.push([p.id,'"'+(p.name||'')+'"',p.phone||'','"'+(p.negocio||'')+'"',p.rubro||'','"'+(p.categoria||'')+'"',p.comuna||'',p.competencia||'',p.procedencia||'','"'+notas+'"',(p.total_tareas>0?'Si':'No'),p.tareas_pendientes||0,(p.created_at||'').substring(0,16),(p.updated_at||'').substring(0,16)].join(','));
    });
    var blob = new Blob(['\\uFEFF'+lines.join('\\n')],{type:'text/csv;charset=utf-8;'});
    var url = URL.createObjectURL(blob);
    var a = document.createElement('a');
    a.href=url; a.download='mp_interesados_'+new Date().toISOString().substring(0,10)+'.csv'; a.click();
    URL.revokeObjectURL(url);
    toast('Exportando '+prospects.length+' interesados','success');
  });
}
"""

content = content.replace('setInterval(checkWaStatus, 30000);', js_fn + 'setInterval(checkWaStatus, 30000);')
print("JS OK:", 'exportarInteresados' in content)

# Verificar despues
print("checkWaStatus despues:", 'function checkWaStatus' in content)
print("loadLeads despues:", 'function loadLeads' in content)

with open('templates/dashboard_test7.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")