with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix el duplicado c.comuna||c.comuna||c.commune
content = content.replace(
    "c.comuna||c.comuna||c.commune||'—'",
    "c.comuna||'—'"
)

# Fix exportLeads que usa l.commune
content = content.replace(
    '"${l.name}","${l.phone}","${l.commune}"',
    '"${l.name}","${l.phone}","${l.comuna}"'
)

# Fix txt search que usa l.commune
content = content.replace(
    'const txt = (l.name+l.phone+l.commune+l.rubro).toLowerCase();',
    'const txt = (l.name+l.phone+(l.comuna||l.commune||"")+l.rubro).toLowerCase();'
)

# Fix scraping comunas render que usa c.comuna||c.commune
content = content.replace(
    '${c.comuna||c.commune}',
    '${c.comuna||"—"}'
)

# Verificar buildWeeklyChart - la semana 14 debe aparecer
print("weekly_sends:", 'weekly_sends' in content)
print("buildWeeklyChart:", 'buildWeeklyChart' in content)

# Fix: asegurar que el grafico semanal usa el campo correcto
# La API devuelve {sent, week, year} - verificar el label
idx = content.find("labels = weekly.map")
print("Weekly labels:", content[idx:idx+80])

# Agregar datos de rubros en loadOverview si no existe
if 'rubrosTable' not in content:
    old_charts = '  // Charts\n  buildWeeklyChart(d.weekly_sends || []);\n  buildDonutChart(d.by_status || {}, d.opt_out || 0);\n}'
    new_charts = '''  // Rubros table
  if(d.top_rubros && d.top_rubros.length && document.getElementById('rubrosTable')){
    document.getElementById('rubrosTable').innerHTML = d.top_rubros.map(function(r){
      var tasa = r.total > 0 ? Math.round((r.interesados||0)/r.total*100) : 0;
      var tc = tasa>=15?'#155724':tasa>=5?'#856404':'#6c757d';
      var tb = tasa>=15?'#d4edda':tasa>=5?'#fff3cd':'#f8f9fa';
      return '<tr><td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 6px;border-radius:8px">'+r.rubro+'</span></td><td style="text-align:center">'+r.total+'</td><td style="text-align:center;color:var(--mp-warn);font-weight:600">'+(r.interesados||0)+'</td><td style="text-align:center;color:var(--mp-green);font-weight:600">'+(r.cerrados||0)+'</td><td style="text-align:center"><span style="padding:2px 6px;border-radius:8px;font-size:11px;font-weight:700;background:'+tb+';color:'+tc+'">'+tasa+'%</span></td></tr>';
    }).join('');
  }
  // Charts
  buildWeeklyChart(d.weekly_sends || []);
  buildDonutChart(d.by_status || {}, d.opt_out || 0);
}'''
    content = content.replace(old_charts, new_charts)
    print("Rubros render agregado")
else:
    print("Rubros render ya existe")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK guardado")