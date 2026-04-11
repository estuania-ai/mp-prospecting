with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Reemplazar render de comunas con grafico de barras horizontal
old_comunas_render = '''  if(d.top_comunas?.length){
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

new_comunas_render = '''  if(d.top_comunas?.length && document.getElementById('comunasList')){
    const maxC = Math.max(...d.top_comunas.map(c=>c.total), 1);
    document.getElementById('comunasList').innerHTML = d.top_comunas.slice(0,8).map(function(c){
      var tasa = c.total > 0 ? Math.round((c.interesados||0)/c.total*100) : 0;
      var pct = Math.round(c.total/maxC*100);
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
  }'''

content = content.replace(old_comunas_render, new_comunas_render)
print("Comunas render OK:", 'justify-content:space-between' in content)

# 2. Reemplazar render de categorias con diseño por rubro
old_cat = '''  if(d.categoria_stats?.length && document.getElementById('categoriasStats')){
    const maxCat = Math.max(...d.categoria_stats.map(c=>c.total), 1);
    document.getElementById('categoriasStats').innerHTML = d.categoria_stats.map(c => {
      const tasa = c.enviados > 0 ? Math.round(c.interesados/c.enviados*100) : 0;
      return '<div style="display:flex;align-items:center;gap:8px;padding:4px 0;border-bottom:1px solid var(--mp-border)">' +
        '<div style="font-size:12px;flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap" title="'+c.categoria+'">'+c.categoria+'</div>' +
        '<div style="display:flex;gap:4px;flex-shrink:0">' +
        '<span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:1px 6px;border-radius:8px">'+c.total+'</span>' +
        (c.interesados>0?'<span style="font-size:11px;background:#fff3cd;color:#856404;padding:1px 6px;border-radius:8px">'+c.interesados+' int.</span>':'') +
        (c.cerrados>0?'<span style="font-size:11px;background:#d4edda;color:#155724;padding:1px 6px;border-radius:8px">'+c.cerrados+' cerr.</span>':'') +
        (tasa>0?'<span style="font-size:11px;font-weight:700;color:'+(tasa>=10?'var(--mp-green)':'var(--mp-text-3)')+'">'+tasa+'%</span>':'') +
        '</div></div>';
    }).join('');
  }'''

new_cat = '''  if(d.categoria_stats?.length && document.getElementById('categoriasStats')){
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
  }'''

content = content.replace(old_cat, new_cat)
print("Categorias render OK:", 'linear-gradient' in content)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK guardado")