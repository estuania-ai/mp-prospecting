"""
mp_fix_export_leads.py
Agrega columnas motivo y notas al export Excel de leads
Trabaja sobre dashboard_test3.html
"""
with open('templates/dashboard_test3.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar funcion exportLeads
idx = content.find('function exportLeads')
end = content.find('\nfunction ', idx+1)
current = content[idx:end]
print("exportLeads actual:")
print(current[:400])
print()

# Reemplazar con version mejorada
old_export = current

new_export = '''function exportLeads(){
  var rows = allLeads || [];
  if(!rows.length){ toast('No hay leads para exportar','error'); return; }

  var headers = ['ID','Negocio','Telefono','Comuna','Rubro','Categoria','Estado','Motivo Rechazo','Notas','Seguimiento 24h','Seguimiento 72h','Fecha actualizacion'];
  var csv = headers.join(',') + '\\n';

  rows.forEach(function(l){
    var estado = statusLabel[l.status] || l.status || '';
    var motivo = (l.optout_motivo || '').replace(/,/g,';');
    var notas  = (l.notes || '').replace(/,/g,';').replace(/\\n/g,' ');
    var seg24  = l.seguimiento_24h ? 'Enviado '+((l.seguimiento_24h_fecha||'').substring(0,10)) : '';
    var seg72  = l.seguimiento_72h ? 'Enviado '+((l.seguimiento_72h_fecha||'').substring(0,10)) : '';
    csv += [
      l.id,
      '"'+(l.name||'').replace(/"/g,"'")+'"',
      l.phone||'',
      l.comuna||l.commune||'',
      l.rubro||'',
      l.categoria||'',
      estado,
      '"'+motivo+'"',
      '"'+notas+'"',
      seg24,
      seg72,
      (l.updated_at||'').substring(0,16)
    ].join(',') + '\\n';
  });

  var blob = new Blob(['\uFEFF'+csv], {type:'text/csv;charset=utf-8;'});
  var url  = URL.createObjectURL(blob);
  var a    = document.createElement('a');
  a.href   = url;
  a.download = 'mp_leads_'+new Date().toISOString().substring(0,10)+'.csv';
  a.click();
  URL.revokeObjectURL(url);
  toast('Exportando '+rows.length+' leads...','success');
}

'''

content = content[:idx] + new_export + content[end:]
print("exportLeads actualizado OK")

# Verificar que allLeads existe en loadLeads
if 'allLeads' not in content:
    content = content.replace(
        'function renderLeads(leads){',
        'var allLeads = [];\nfunction renderLeads(leads){\n  allLeads = leads;'
    )
    print("allLeads agregado OK")
else:
    print("allLeads ya existe")

# Agregar campo notes y optout_motivo en la query de leads si no esta
with open('routes/leads.py', 'r', encoding='utf-8') as f:
    leads_py = f.read()

if 'ls.notes' not in leads_py:
    print("ADVERTENCIA: ls.notes no esta en la query de leads")
else:
    print("ls.notes ya existe en query OK")

with open('templates/dashboard_test3.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
