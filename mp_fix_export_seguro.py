with open('templates/dashboard_test5.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function exportLeads()')
end = content.find('\nfunction toggleAllSellers', idx+1)

print("Reemplazando exportLeads:", idx, "->", end)

new_fn = '''function exportLeads(){
  var rows = allLeads || [];
  if(!rows.length){ toast('No hay leads para exportar', 'error'); return; }
  var headers = ['ID','Negocio','Telefono','Comuna','Rubro','Categoria','Estado','Motivo Opt-out','Notas','Fecha Seguimiento 24h','Fecha Seguimiento 72h','Fecha actualizacion'];
  var lines = [headers.join(',')];
  rows.forEach(function(l){
    var estado = statusLabel[l.status] || l.status || '';
    var motivo = (l.optout_motivo||'').replace(/,/g,';').replace(/"/g,"'");
    var notas  = (l.notes||'').replace(/,/g,';').replace(/\\n/g,' ').replace(/"/g,"'");
    var seg24  = l.seguimiento_24h && l.seguimiento_24h_fecha ? (l.seguimiento_24h_fecha||'').substring(0,16) : '';
    var seg72  = l.seguimiento_72h && l.seguimiento_72h_fecha ? (l.seguimiento_72h_fecha||'').substring(0,16) : '';
    lines.push([
      l.id,
      '"'+(l.name||'').replace(/"/g,"'")+'"',
      l.phone||'',
      '"'+(l.comuna||l.commune||'')+'"',
      l.rubro||'',
      '"'+(l.categoria||'')+'"',
      estado,
      '"'+motivo+'"',
      '"'+notas+'"',
      seg24, seg72,
      (l.updated_at||'').substring(0,16)
    ].join(','));
  });
  var blob = new Blob(['\uFEFF'+lines.join('\n')],{type:'text/csv;charset=utf-8;'});
  var url = URL.createObjectURL(blob);
  var a = document.createElement('a');
  a.href = url;
  a.download = 'mp_prospeccion_'+new Date().toISOString().substring(0,10)+'.csv';
  a.click();
  URL.revokeObjectURL(url);
  toast('Exportando '+rows.length+' leads','success');
}

'''

content = content[:idx] + new_fn + content[end:]

print("checkWaStatus OK:", 'function checkWaStatus' in content)
print("loadLeads OK:", 'function loadLeads' in content)
print("loadOverview OK:", 'function loadOverview' in content)
print("renderLeads OK:", 'function renderLeads' in content)

with open('templates/dashboard_test5.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")