with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix top_comunas: c.commune -> c.comuna
old_comunas = '''  if(d.top_comunas?.length){
    const maxC = d.top_comunas[0].total;
    document.getElementById('comunasList').innerHTML = d.top_comunas.slice(0,8).map(c =>
      `<div class="commune-row">
        <div class="commune-name">${c.commune}</div>
        <div class="commune-track"><div class="commune-bar" style="width:${Math.round(c.total/maxC*100)}%"></div></div>
        <div class="commune-val">${c.total}</div>
      </div>`
    ).join('');
  }'''

new_comunas = '''  if(d.top_comunas?.length){
    const maxC = d.top_comunas[0].total;
    document.getElementById('comunasList').innerHTML = d.top_comunas.slice(0,8).map(c => {
      const tasa = c.total > 0 ? Math.round((c.interesados||0)/c.total*100) : 0;
      return '<div class="commune-row">' +
        '<div class="commune-name">' + (c.comuna||c.commune||'—') + '</div>' +
        '<div class="commune-track"><div class="commune-bar" style="width:'+Math.round(c.total/maxC*100)+'%"></div></div>' +
        '<div class="commune-val">' + c.total + '</div>' +
        (tasa>0 ? '<span style="font-size:11px;font-weight:700;color:var(--mp-warn);margin-left:6px">'+tasa+'%</span>' : '') +
        '</div>';
    }).join('');
  }'''

content = content.replace(old_comunas, new_comunas)
print("Comunas fix:", 'c.comuna||c.commune' in content)

# 2. Fix donut chart - agregar no_enviado
old_donut_map = '''  const map = [
    {key:'enviado', label:'Enviados', color:'#009ee3'},
    {key:'abierto', label:'Abiertos', color:'#3d5a99'},
    {key:'interesado', label:'Interesados', color:'#b8860b'},
    {key:'quiere_reunion', label:'Reunión', color:'#7b3fe4'},
    {key:'cerrado', label:'Cerrados', color:'#00a650'},
    {key:'no_interesado', label:'No int.', color:'#f23d4f'},
  ];'''

new_donut_map = '''  const map = [
    {key:'no_enviado', label:'No enviado', color:'#adb5bd'},
    {key:'enviado', label:'Enviados', color:'#009ee3'},
    {key:'abierto', label:'Abiertos', color:'#3d5a99'},
    {key:'interesado', label:'Interesados', color:'#b8860b'},
    {key:'quiere_reunion', label:'Reunion', color:'#7b3fe4'},
    {key:'cerrado', label:'Cerrados', color:'#00a650'},
    {key:'no_interesado', label:'No int.', color:'#f23d4f'},
  ];'''

content = content.replace(old_donut_map, new_donut_map)
print("Donut fix:", 'no_enviado' in content)

# 3. Fix weekly chart - usar fecha legible
old_weekly = '''  const labels = weekly.map(w => 'Sem '+w.week).reverse();
  const data   = weekly.map(w => w.sent).reverse();'''

new_weekly = '''  const labels = weekly.map(w => 'Sem '+w.week+(w.year?' '+w.year:'')).reverse();
  const data   = weekly.map(w => w.sent).reverse();'''

content = content.replace(old_weekly, new_weekly)
print("Weekly fix:", "w.year?' '+w.year:''" in content)

# 4. Agregar cuadro de rubros despues de comunas en el HTML
old_comunas_card = '''<div class="card">
    <div class="card-title"><span class="card-icon">🏙️</span>Top comunas</div>'''

new_rubros_card = '''<div class="card">
    <div class="card-title"><span class="card-icon">📊</span>Rubros prospectados y tasa de respuesta</div>
    <div class="table-wrap" style="border-radius:8px;max-height:220px;overflow-y:auto">
      <table>
        <thead><tr>
          <th>Rubro</th>
          <th style="text-align:center">Leads</th>
          <th style="text-align:center">Interesados</th>
          <th style="text-align:center">Cerrados</th>
          <th style="text-align:center">Tasa</th>
        </tr></thead>
        <tbody id="rubrosTable"></tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-title"><span class="card-icon">🏙️</span>Top comunas</div>'''

content = content.replace(old_comunas_card, new_rubros_card)
print("Rubros card:", 'rubrosTable' in content)

# 5. Agregar render de rubros en loadOverview
old_charts = '''  // Charts
  buildWeeklyChart(d.weekly_sends || []);
  buildDonutChart(d.by_status || {}, d.opt_out || 0);
}'''

new_charts = '''  // Tabla rubros
  if(d.top_rubros?.length){
    const maxR = Math.max(...d.top_rubros.map(r=>r.total), 1);
    document.getElementById('rubrosTable').innerHTML = d.top_rubros.map(function(r){
      var tasa = r.total > 0 ? Math.round((r.interesados||0)/r.total*100) : 0;
      var tasaColor = tasa>=15 ? '#155724' : tasa>=5 ? '#856404' : '#6c757d';
      var tasaBg = tasa>=15 ? '#d4edda' : tasa>=5 ? '#fff3cd' : '#f8f9fa';
      return '<tr>' +
        '<td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">'+r.rubro+'</span></td>' +
        '<td style="text-align:center;font-weight:600">'+r.total+'</td>' +
        '<td style="text-align:center;color:var(--mp-warn);font-weight:600">'+(r.interesados||0)+'</td>' +
        '<td style="text-align:center;color:var(--mp-green);font-weight:600">'+(r.cerrados||0)+'</td>' +
        '<td style="text-align:center"><span style="padding:2px 8px;border-radius:10px;font-size:11px;font-weight:700;background:'+tasaBg+';color:'+tasaColor+'">'+tasa+'%</span></td>' +
        '</tr>';
    }).join('');
  }

  // Charts
  buildWeeklyChart(d.weekly_sends || []);
  buildDonutChart(d.by_status || {}, d.opt_out || 0);
}'''

content = content.replace(old_charts, new_charts)
print("Rubros render:", 'rubrosTable' in content and 'top_rubros' in content)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerificaciones finales:")
print("Comunas OK:", 'c.comuna||c.commune' in content)
print("Donut no_enviado OK:", "'no_enviado', label:'No enviado'" in content)
print("Weekly year OK:", "w.year?' '+w.year:''" in content)
print("Rubros card OK:", 'rubrosTable' in content)
print("LISTO")
