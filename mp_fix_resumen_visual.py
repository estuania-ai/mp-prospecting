"""
mp_fix_resumen_visual.py
Mejora visual del Resumen:
1. Top comunas con barra de progreso y % interesados
2. Leads por categoria con barras y badges
3. Rubros prospectados con tabla coloreada
Aplicar sobre mp_dashboard_ESTABLE.html
"""

with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. TOP COMUNAS - mejorar render ──────────────────
old_comunas = """  if(d.top_comunas && d.top_comunas.length && document.getElementById('comunasList')){
    var maxC2 = Math.max.apply(null, d.top_comunas.map(function(c){return c.total;}));
    if(maxC2<=0) maxC2=1;
    document.getElementById('comunasList').innerHTML = d.top_comunas.slice(0,8).map(function(c){
      var tasa = c.total > 0 ? Math.round((c.interesados||0)/c.total*100) : 0;
      var pct = Math.round(c.total/maxC2*100);
      return '<div style="margin-bottom:10px">' +
        '<div style="display:flex;justify-content:space-between;margin-bottom:3px">' +
        '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1)">' + (c.comuna||'—') + '</span>' +
        '<div style="display:flex;gap:6px;align-items:center">' +
        '<span style="font-size:11px;color:var(--mp-text-3)">' + c.total + ' leads</span>' +
        (tasa>0?'<span style="font-size:11px;font-weight:700;color:var(--mp-warn);background:#fff3cd;padding:1px 6px;border-radius:8px">'+tasa+'% int.</span>':'') +
        '</div></div>' +
        '<div style="background:#eef2f7;border-radius:4px;height:8px;overflow:hidden">' +
        '<div style="height:100%;border-radius:4px;background:var(--mp-blue);width:'+pct+'%;transition:width .5s"></div>' +
        '</div></div>';
    }).join('');
  }"""

new_comunas = """  if(d.top_comunas && d.top_comunas.length && document.getElementById('comunasList')){
    var maxC2 = Math.max.apply(null, d.top_comunas.map(function(c){return c.total;}));
    if(maxC2<=0) maxC2=1;
    document.getElementById('comunasList').innerHTML = d.top_comunas.slice(0,8).map(function(c){
      var tasa = c.total > 0 ? Math.round((c.interesados||0)/c.total*100) : 0;
      var pct = Math.round(c.total/maxC2*100);
      var barColor = tasa>=15?'linear-gradient(90deg,#00a650,#00d084)':tasa>=5?'linear-gradient(90deg,#f0a500,#ffd000)':'linear-gradient(90deg,#009ee3,#00c9ff)';
      var tasaBadge = tasa>0 ? '<span style="font-size:10px;font-weight:700;padding:1px 8px;border-radius:10px;background:'+(tasa>=15?'#d4edda':'#fff3cd')+';color:'+(tasa>=15?'#155724':'#856404')+'">'+tasa+'% int.</span>' : '<span style="font-size:10px;color:var(--mp-text-3)">sin respuesta</span>';
      return '<div style="margin-bottom:14px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">' +
        '<span style="font-size:13px;font-weight:700;color:var(--mp-text-1)">' + (c.comuna||'—') + '</span>' +
        '<div style="display:flex;gap:6px;align-items:center">' +
        '<span style="font-size:11px;font-weight:600;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">' + c.total + ' leads</span>' +
        tasaBadge +
        '</div></div>' +
        '<div style="background:#eef2f7;border-radius:6px;height:10px;overflow:hidden">' +
        '<div style="height:100%;border-radius:6px;background:'+barColor+';width:'+pct+'%;transition:width .6s"></div>' +
        '</div></div>';
    }).join('');
  }"""

if old_comunas in content:
    content = content.replace(old_comunas, new_comunas)
    print("1. Comunas OK")
else:
    print("1. Comunas - texto no encontrado, buscando alternativa...")
    idx = content.find("getElementById('comunasList')")
    print("   pos:", idx)

# ── 2. CATEGORIAS - mejorar render ───────────────────
old_cat = """  if(d.categoria_stats?.length && document.getElementById('categoriasStats')){
    var maxCatLeads = Math.max.apply(null, d.categoria_stats.map(function(c){return c.total;}));
    if(maxCatLeads<=0) maxCatLeads=1;
    document.getElementById('categoriasStats').innerHTML = d.categoria_stats.map(function(c){
      var tasa = c.enviados > 0 ? Math.round(c.interesados/c.enviados*100) : 0;
      var pct = Math.round(c.total/maxCatLeads*100);
      var tc = tasa>=15?'#155724':tasa>=5?'#856404':'#6c757d';
      var tb = tasa>=15?'#d4edda':tasa>=5?'#fff3cd':'#f8f9fa';
      return '<div style="margin-bottom:12px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">' +
        '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1);flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+c.categoria+'">'+c.categoria+'</span>' +
        '<div style="display:flex;gap:4px;margin-left:8px;flex-shrink:0">' +
        '<span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:1px 8px;border-radius:10px;font-weight:600">'+c.total+'</span>' +
        (c.pendientes>0?'<span style="font-size:11px;background:#f8f9fa;color:#495057;padding:1px 8px;border-radius:10px;border:1px solid #ced4da">'+c.pendientes+' pend.</span>':'') +
        (c.interesados>0?'<span style="font-size:11px;background:#fff3cd;color:#856404;padding:1px 8px;border-radius:10px;font-weight:600">'+c.interesados+' int.</span>':'') +
        (c.cerrados>0?'<span style="font-size:11px;background:#d4edda;color:#155724;padding:1px 8px;border-radius:10px;font-weight:600">'+c.cerrados+' cerr.</span>':'') +
        (tasa>0?'<span style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:10px;background:'+tb+';color:'+tc+'">'+tasa+'%</span>':'') +
        '</div></div>' +
        '<div style="background:#eef2f7;border-radius:4px;height:6px;overflow:hidden">' +
        '<div style="height:100%;border-radius:4px;background:linear-gradient(90deg,var(--mp-blue),#00c9ff);width:'+pct+'%;transition:width .6s"></div>' +
        '</div></div>';
    }).join('');
  }"""

# Si no existe, buscar version basica y mejorarla
if old_cat not in content:
    # Buscar cualquier version de categoriasStats render
    idx_cat = content.find("getElementById('categoriasStats').innerHTML")
    if idx_cat > 0:
        # Encontrar el bloque completo
        block_start = content.rfind('\n  if(', 0, idx_cat)
        block_end = content.find('\n  }', idx_cat) + 4
        old_cat = content[block_start:block_end]
        print("2. Categorias - encontrado bloque alternativo")
    else:
        print("2. Categorias - no hay render, agregando...")
        old_cat = None

new_cat = """  if(d.categoria_stats && d.categoria_stats.length && document.getElementById('categoriasStats')){
    var maxCat2 = Math.max.apply(null, d.categoria_stats.map(function(c){return c.total;}));
    if(maxCat2<=0) maxCat2=1;
    document.getElementById('categoriasStats').innerHTML = d.categoria_stats.map(function(c){
      var tasa = c.enviados > 0 ? Math.round(c.interesados/c.enviados*100) : 0;
      var pct = Math.round(c.total/maxCat2*100);
      var tc = tasa>=15?'#155724':tasa>=5?'#856404':'#6c757d';
      var tb = tasa>=15?'#d4edda':tasa>=5?'#fff3cd':'#f8f9fa';
      return '<div style="margin-bottom:14px">' +
        '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:5px">' +
        '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1);flex:1;white-space:nowrap;overflow:hidden;text-overflow:ellipsis" title="'+c.categoria+'">'+c.categoria+'</span>' +
        '<div style="display:flex;gap:4px;margin-left:8px;flex-shrink:0">' +
        '<span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:1px 8px;border-radius:10px;font-weight:600">'+c.total+'</span>' +
        (c.pendientes>0?'<span style="font-size:11px;background:#f8f9fa;color:#495057;padding:1px 8px;border-radius:10px;border:1px solid #ced4da">'+c.pendientes+' pend.</span>':'') +
        (c.interesados>0?'<span style="font-size:11px;background:#fff3cd;color:#856404;padding:1px 8px;border-radius:10px;font-weight:600">'+c.interesados+' int.</span>':'') +
        (c.cerrados>0?'<span style="font-size:11px;background:#d4edda;color:#155724;padding:1px 8px;border-radius:10px;font-weight:600">'+c.cerrados+' cerr.</span>':'') +
        (tasa>0?'<span style="font-size:11px;font-weight:700;padding:1px 8px;border-radius:10px;background:'+tb+';color:'+tc+'">'+tasa+'%</span>':'') +
        '</div></div>' +
        '<div style="background:#eef2f7;border-radius:6px;height:8px;overflow:hidden">' +
        '<div style="height:100%;border-radius:6px;background:linear-gradient(90deg,var(--mp-blue),#00c9ff);width:'+pct+'%;transition:width .7s"></div>' +
        '</div></div>';
    }).join('');
  }"""

if old_cat:
    content = content.replace(old_cat, new_cat)
    print("2. Categorias OK")

# ── 3. RUBROS - mejorar tabla ────────────────────────
old_rubros = """  if(d.top_rubros && d.top_rubros.length && document.getElementById('rubrosTable')){
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
  }"""

new_rubros = """  if(d.top_rubros && d.top_rubros.length && document.getElementById('rubrosTable')){
    var maxR2 = Math.max.apply(null, d.top_rubros.map(function(r){return r.total;}));
    if(maxR2<=0) maxR2=1;
    document.getElementById('rubrosTable').innerHTML = d.top_rubros.map(function(r){
      var tasa = r.total > 0 ? Math.round((r.interesados||0)/r.total*100) : 0;
      var tc = tasa>=15?'#155724':tasa>=5?'#856404':'#6c757d';
      var tb = tasa>=15?'#d4edda':tasa>=5?'#fff3cd':'#f8f9fa';
      var pct = Math.round(r.total/maxR2*100);
      return '<tr>' +
        '<td>' +
        '<div><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">'+r.rubro+'</span></div>' +
        '<div style="background:#eef2f7;border-radius:3px;height:4px;margin-top:3px;overflow:hidden">' +
        '<div style="height:100%;border-radius:3px;background:var(--mp-blue);width:'+pct+'%"></div>' +
        '</div></td>' +
        '<td style="text-align:center;font-weight:700;color:var(--mp-blue)">'+r.total+'</td>' +
        '<td style="text-align:center;font-weight:700;color:#856404">'+(r.interesados||0)+'</td>' +
        '<td style="text-align:center;font-weight:700;color:var(--mp-green)">'+(r.cerrados||0)+'</td>' +
        '<td style="text-align:center"><span style="padding:2px 10px;border-radius:10px;font-size:11px;font-weight:700;background:'+tb+';color:'+tc+'">'+tasa+'%</span></td>' +
        '</tr>';
    }).join('');
  }"""

if old_rubros in content:
    content = content.replace(old_rubros, new_rubros)
    print("3. Rubros OK")
else:
    print("3. Rubros - buscando alternativa...")
    idx_rub = content.find("getElementById('rubrosTable').innerHTML")
    if idx_rub > 0:
        print("   rubrosTable render encontrado en pos:", idx_rub)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerificaciones:")
print("Comunas gradiente:", 'linear-gradient(90deg,#00a650' in content)
print("Categorias gradiente:", 'linear-gradient(90deg,var(--mp-blue)' in content)
print("LISTO")
