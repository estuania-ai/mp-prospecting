"""
mp_fix_export_leads_test4.py
Mejora exportacion de leads con columnas:
- Motivo Opt-out
- Notas
- Seguimiento 24h
- Seguimiento 72h
Trabaja sobre dashboard_test4.html
"""
with open('templates/dashboard_test4.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar funcion exportLeads
idx = content.find('function exportLeads()')
end = content.find('\nfunction ', idx+1)
old_fn = content[idx:end]
print("exportLeads encontrado en pos:", idx)

new_fn = '''function exportLeads(){
  var rows = allLeads || [];
  if(!rows.length){ toast('No hay leads para exportar', 'error'); return; }

  var headers = ['ID','Negocio','Telefono','Comuna','Rubro','Categoria','Estado',
                 'Motivo Opt-out','Notas','Seguimiento 24h','Seguimiento 72h',
                 'Fecha actualizacion'];
  var lines = [headers.join(',')];

  rows.forEach(function(l){
    var estado  = statusLabel[l.status] || l.status || '';
    var motivo  = (l.optout_motivo || '').replace(/,/g,';');
    var notas   = (l.notes || '').replace(/,/g,';').replace(/\\n/g,' ');
    var seg24   = l.seguimiento_24h ? 'Enviado ' + ((l.seguimiento_24h_fecha||'').substring(0,10)) : '';
    var seg72   = l.seguimiento_72h ? 'Enviado ' + ((l.seguimiento_72h_fecha||'').substring(0,10)) : '';
    lines.push([
      l.id,
      '"' + (l.name||'').replace(/"/g,"'") + '"',
      l.phone || '',
      l.comuna || l.commune || '',
      l.rubro || '',
      l.categoria || '',
      estado,
      '"' + motivo + '"',
      '"' + notas + '"',
      seg24,
      seg72,
      (l.updated_at||'').substring(0,16)
    ].join(','));
  });

  var csv  = lines.join('\\n');
  var blob = new Blob(['\\uFEFF' + csv], {type:'text/csv;charset=utf-8;'});
  var url  = URL.createObjectURL(blob);
  var a    = document.createElement('a');
  a.href   = url;
  a.download = 'mp_prospeccion_' + new Date().toISOString().substring(0,10) + '.csv';
  a.click();
  URL.revokeObjectURL(url);
  toast('Exportando ' + rows.length + ' leads...', 'success');
}

'''

content = content[:idx] + new_fn + content[end:]
print("exportLeads actualizado OK")

with open('templates/dashboard_test4.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
