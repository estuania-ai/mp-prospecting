"""
mp_fix_resumen_rechazos.py
Trabajar sobre dashboard_test3.html:
1. Cuadro de rechazos con motivos opt-out graficados
2. Distribucion de estados con datos reales
3. Export leads con columna motivo y notas
"""

with open('templates/dashboard_test3.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Agregar cuadro de rechazos despues del donut ──
old_donut_card = '''    <div class="card">
      <div class="card-title"><span class="card-icon">🍩</span>Distribucion de estados</div>
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <div class="chart-wrap chart-h160" style="width:160px;flex-shrink:0">
          <canvas id="chartDonut"></canvas>
        </div>
        <div id="donutLegend" style="display:flex;flex-direction:column;gap:7px;font-size:12px"></div>
      </div>
    </div>'''

new_donut_card = '''    <div class="card">
      <div class="card-title"><span class="card-icon">🍩</span>Distribucion de estados</div>
      <div style="display:flex;gap:16px;align-items:center;flex-wrap:wrap">
        <div class="chart-wrap chart-h160" style="width:160px;flex-shrink:0">
          <canvas id="chartDonut"></canvas>
        </div>
        <div id="donutLegend" style="display:flex;flex-direction:column;gap:7px;font-size:12px;flex:1"></div>
      </div>
      <div id="statusBarsResumen" style="margin-top:12px;display:flex;flex-direction:column;gap:5px"></div>
    </div>

    <div class="card">
      <div class="card-title"><span class="card-icon">🚫</span>Analisis de rechazos y opt-out</div>
      <div style="font-size:11px;color:var(--mp-text-3);margin-bottom:12px">Motivos de no conversion — tomar accion</div>
      <div id="rechazosStats"></div>
    </div>'''

if old_donut_card in content:
    content = content.replace(old_donut_card, new_donut_card)
    print("1. Cuadro rechazos agregado OK")
else:
    print("1. No encontrado - buscando alternativa...")
    idx = content.find('chartDonut')
    print("chartDonut pos:", idx)

# ── 2. Agregar render rechazos en loadOverview ────────
old_donut_call = '  buildDonutChart(d.by_status || {}, d.opt_out || 0);'
new_donut_call = '''  buildDonutChart(d.by_status || {}, d.opt_out || 0);

  // Barras de estado
  if(document.getElementById('statusBarsResumen')){
    var statusItems = [
      {key:'no_enviado',     lbl:'No enviado',     color:'#adb5bd'},
      {key:'enviado',        lbl:'Enviado',         color:'#009ee3'},
      {key:'interesado',     lbl:'Interesado',      color:'#b8860b'},
      {key:'quiere_reunion', lbl:'Quiere reunion',  color:'#7b3fe4'},
      {key:'cerrado',        lbl:'Cerrado',         color:'#00a650'},
      {key:'no_interesado',  lbl:'No interesado',   color:'#f23d4f'},
      {key:'opt_out',        lbl:'Opt-out',         color:'#fd7e14'},
    ];
    var totalL = d.total_leads || 1;
    document.getElementById('statusBarsResumen').innerHTML = statusItems.map(function(s){
      var cnt = d.by_status[s.key] || 0;
      if(cnt===0) return '';
      var pct = Math.round(cnt/totalL*100);
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:4px">' +
        '<div style="width:10px;height:10px;border-radius:2px;background:'+s.color+';flex-shrink:0"></div>' +
        '<span style="font-size:11px;color:var(--mp-text-2);min-width:115px">'+s.lbl+'</span>' +
        '<div style="flex:1;background:#eef2f7;border-radius:4px;height:6px;overflow:hidden">' +
        '<div style="height:100%;border-radius:4px;background:'+s.color+';width:'+pct+'%"></div>' +
        '</div>' +
        '<span style="font-size:11px;font-weight:700;color:var(--mp-text-1);min-width:20px;text-align:right">'+cnt+'</span>' +
        '<span style="font-size:10px;color:var(--mp-text-3);min-width:30px">'+pct+'%</span>' +
        '</div>';
    }).join('');
  }

  // Rechazos y motivos opt-out
  if(document.getElementById('rechazosStats') && d.optout_motivos){
    var totalRechazos = (d.by_status.no_interesado||0) + (d.by_status.opt_out||0) + d.opt_out;
    var maxMotivo = Math.max.apply(null, d.optout_motivos.map(function(m){return m.total;}));
    if(maxMotivo<=0) maxMotivo=1;

    var html = '<div style="display:flex;gap:12px;margin-bottom:16px;flex-wrap:wrap">' +
      '<div style="flex:1;min-width:120px;background:#fff5f5;border-radius:10px;padding:12px;text-align:center">' +
      '<div style="font-size:22px;font-weight:800;color:#f23d4f">' + (d.by_status.no_interesado||0) + '</div>' +
      '<div style="font-size:11px;color:#f23d4f">No interesados</div></div>' +
      '<div style="flex:1;min-width:120px;background:#fff3e0;border-radius:10px;padding:12px;text-align:center">' +
      '<div style="font-size:22px;font-weight:800;color:#fd7e14">' + (d.by_status.opt_out||0) + '</div>' +
      '<div style="font-size:11px;color:#fd7e14">Opt-out</div></div>' +
      '<div style="flex:1;min-width:120px;background:#f8f9fa;border-radius:10px;padding:12px;text-align:center">' +
      '<div style="font-size:22px;font-weight:800;color:#6c757d">' + totalRechazos + '</div>' +
      '<div style="font-size:11px;color:#6c757d">Total rechazos</div></div>' +
      '</div>';

    if(d.optout_motivos.length){
      html += '<div style="font-size:12px;font-weight:600;color:var(--mp-text-2);margin-bottom:8px">Motivos de rechazo:</div>';
      html += d.optout_motivos.map(function(m){
        var pct = Math.round(m.total/maxMotivo*100);
        var colors = {
          'Sin interes':'#f23d4f','Sin respuesta':'#fd7e14',
          'Tiene MP':'#009ee3','Precio':'#856404','Otro':'#6c757d'
        };
        var color = colors[m.motivo] || '#6c757d';
        return '<div style="margin-bottom:10px">' +
          '<div style="display:flex;justify-content:space-between;margin-bottom:3px">' +
          '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1)">' + m.motivo + '</span>' +
          '<span style="font-size:11px;font-weight:700;background:#f8f9fa;padding:1px 8px;border-radius:8px">' + m.total + ' casos</span>' +
          '</div>' +
          '<div style="background:#eef2f7;border-radius:6px;height:10px;overflow:hidden">' +
          '<div style="height:100%;border-radius:6px;background:'+color+';width:'+pct+'%;transition:width .6s"></div>' +
          '</div></div>';
      }).join('');
    } else {
      html += '<div style="color:var(--mp-text-3);font-size:12px;padding:12px;text-align:center">Sin rechazos registrados aun</div>';
    }

    // Accion sugerida
    if(d.optout_motivos.length){
      var topMotivo = d.optout_motivos[0];
      var acciones = {
        'Sin interes': 'Revisar el pitch inicial y mensaje de prospeccion',
        'Sin respuesta': 'Aumentar seguimientos o probar nuevo horario de envio',
        'Tiene MP': 'Solicitar referidos — estos prospectos ya conocen el producto',
        'Precio': 'Reforzar propuesta de valor y beneficios del POS',
        'Otro': 'Revisar notas individuales para identificar patron'
      };
      var accion = acciones[topMotivo.motivo] || 'Revisar leads manualmente';
      html += '<div style="background:#e8f4fd;border-radius:8px;padding:10px 12px;margin-top:8px;font-size:12px">' +
        '<strong style="color:#009ee3">Accion sugerida:</strong> ' + accion + '</div>';
    }

    document.getElementById('rechazosStats').innerHTML = html;
  }'''

content = content.replace(old_donut_call, new_donut_call)
print("2. Render rechazos OK:", 'rechazosStats' in content)

with open('templates/dashboard_test3.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO dashboard")
