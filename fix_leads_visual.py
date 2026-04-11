with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Eliminar boton verde WA de la tabla leads (solo dejar lapiz)
old_btns = '''        <div style="display:flex;gap:4px">
          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},'${l.status||'no_enviado'}')">✏️</button>
          <button class="btn btn-green btn-sm" onclick="openWA('${l.phone}')" title="Abrir WhatsApp">💬</button>
        </div>'''
new_btns = '''        <div style="display:flex;gap:4px">
          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},'${l.status||\'no_enviado\'}')">✏️</button>
          <button class="btn btn-ghost btn-sm" onclick="openWA(\'${l.phone}\')" title="Abrir chat WhatsApp" style="font-size:14px;padding:2px 6px">💬</button>
        </div>'''

# Try simpler approach - find and remove the green btn
if 'btn-green btn-sm" onclick="openWA' in content:
    content = content.replace(
        'class="btn btn-green btn-sm" onclick="openWA(\'${l.phone}\')" title="Abrir WhatsApp">💬</button>',
        'class="btn btn-ghost btn-sm" onclick="openWA(\'${l.phone}\')" title="WhatsApp" style="font-size:12px">💬</button>'
    )
    print("Boton verde corregido")
elif '<a href="https://wa.me/${l.phone' in content:
    content = content.replace(
        '<a href="https://wa.me/${l.phone?.replace(/\\D/g,\'\')}" target="_blank" class="btn btn-green btn-sm">💬</a>',
        '<button class="btn btn-ghost btn-sm" onclick="openWA(\'${l.phone}\')" title="WhatsApp">💬</button>'
    )
    print("Boton verde (link) corregido")
else:
    print("Boton no encontrado - buscando...")
    idx = content.find('btn-green')
    while idx > 0:
        print("  btn-green en:", idx, "->", content[idx:idx+80])
        idx = content.find('btn-green', idx+1)

# 2. Agregar seccion de metricas por categoria en Resumen
old_comunas_section = '<div class="card">\n    <div class="card-title"><span class="card-icon">🏙️</span>Top comunas</div>'
new_comunas_section = '''<div class="card">
    <div class="card-title"><span class="card-icon">📦</span>Leads por categoria</div>
    <div id="categoriasStats" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto"></div>
  </div>

  <div class="card">
    <div class="card-title"><span class="card-icon">🏙️</span>Top comunas</div>'''

content = content.replace(old_comunas_section, new_comunas_section)
print("Seccion categorias:", 'categoriasStats' in content)

# 3. Agregar render de categorias en loadOverview
old_comunas_render = "  if(d.top_comunas?.length){"
new_categorias_render = """  // Categorias stats
  if(d.categoria_stats?.length){
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
  }

  if(d.top_comunas?.length){"""

content = content.replace(old_comunas_render, new_categorias_render)
print("Render categorias:", 'categoriasStats' in content and 'categoria_stats' in content)

# 4. Actualizar total_sent en KPI para contar todos los mensajes
old_sent_kpi = "document.getElementById('kpi-sent').textContent    = fmt(d.total_sent);"
new_sent_kpi = "document.getElementById('kpi-sent').textContent    = fmt(d.total_sent);\n  document.getElementById('kpi-leads').textContent   = fmt(d.total_leads);"
# Already handled, skip

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
