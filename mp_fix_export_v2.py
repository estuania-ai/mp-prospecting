with open('templates/dashboard_test5.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """function exportLeads(){
  const headers = 'Nombre,Teléfono,Comuna,Rubro,Estado,Enviado';
  const rows = allLeads.map(l =>
    `"${l.name}","${l.phone}","${l.comuna}","${l.rubro}","${l.status||'enviado'}","${l.sent_at||''}"`
  );
  const blob = new Blob([headers+'\\n'+rows.join('\\n')], {type:'text/csv'});
  const a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = `leads_mp_${new Date().toISOString().slice(0,10)}.csv`;
  a.click();
  toast('CSV exportado','success"""

new = """function exportLeads(){
  var hdrs = ['ID','Negocio','Telefono','Comuna','Rubro','Categoria','Estado','Motivo Opt-out','Notas','Fecha Seg 24h','Fecha Seg 72h','Ultima actualizacion'];
  var lines = [hdrs.join(',')];
  (allLeads||[]).forEach(function(l){
    var estado = statusLabel[l.status]||l.status||'';
    var motivo = (l.optout_motivo||'').replace(/,/g,';');
    var notas  = (l.notes||'').replace(/,/g,';').replace(/\\n/g,' ');
    var seg24  = l.seguimiento_24h_fecha ? (l.seguimiento_24h_fecha||'').substring(0,16) : '';
    var seg72  = l.seguimiento_72h_fecha ? (l.seguimiento_72h_fecha||'').substring(0,16) : '';
    lines.push([
      l.id,
      '"'+(l.name||'')+'"',
      l.phone||'',
      l.comuna||l.commune||'',
      l.rubro||'',
      l.categoria||'',
      estado,
      '"'+motivo+'"',
      '"'+notas+'"',
      seg24, seg72,
      (l.updated_at||'').substring(0,16)
    ].join(','));
  });
  var blob = new Blob(['\\uFEFF'+lines.join('\\n')],{type:'text/csv;charset=utf-8;'});
  var a = document.createElement('a');
  a.href = URL.createObjectURL(blob);
  a.download = 'mp_prospeccion_'+new Date().toISOString().slice(0,10)+'.csv';
  a.click();
  toast('CSV exportado','success"""

if old in content:
    content = content.replace(old, new)
    print("OK reemplazado")
else:
    print("No encontrado")

# Verificar funciones clave intactas
print("loadLeads:", 'function loadLeads' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)
print("renderLeads:", 'function renderLeads' in content)

with open('templates/dashboard_test5.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")