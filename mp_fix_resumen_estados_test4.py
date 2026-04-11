"""
mp_fix_resumen_estados_test4.py
Agrega en Resumen:
1. Cuadro distribucion de estados con barras
2. Cuadro analisis de rechazos con motivos opt-out graficados
Trabaja sobre dashboard_test4.html
"""
with open('templates/dashboard_test4.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ── 1. Agregar cuadro rechazos en HTML ───────────────
# Buscar el card del donut
idx_donut = content.find('id="chartDonut"')
card_start = content.rfind('<div class="card">', 0, idx_donut)
card_end = content.find('</div>\n  </div>', idx_donut) + 15

old_donut_card = content[card_start:card_end]

new_donut_card = old_donut_card.replace(
    'id="donutLegend"',
    'id="donutLegend" style="flex:1"'
) + '''

  <div class="card">
    <div class="card-title"><span class="card-icon">📊</span>Estados de leads</div>
    <div style="font-size:11px;color:var(--mp-text-3);margin-bottom:10px">Distribucion por estado sobre el total de leads</div>
    <div id="statusBarsResumen"></div>
  </div>

  <div class="card">
    <div class="card-title"><span class="card-icon">🚫</span>Analisis de rechazos</div>
    <div style="font-size:11px;color:var(--mp-text-3);margin-bottom:10px">Motivos opt-out y no interesados — tomar accion</div>
    <div id="rechazosStats"></div>
  </div>'''

content = content.replace(old_donut_card, new_donut_card)
print("1. Cards rechazos agregados:", 'rechazosStats' in content and 'statusBarsResumen' in content)

# ── 2. Agregar render en loadOverview ────────────────
old_charts = '  buildDonutChart(d.by_status || {}, d.opt_out || 0);\n}'
new_charts = '''  buildDonutChart(d.by_status || {}, d.opt_out || 0);

  // Barras de estados
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
      return '<div style="display:flex;align-items:center;gap:8px;margin-bottom:6px">' +
        '<div style="width:10px;height:10px;border-radius:2px;background:'+s.color+';flex-shrink:0"></div>' +
        '<span style="font-size:12px;color:var(--mp-text-2);min-width:120px">'+s.lbl+'</span>' +
        '<div style="flex:1;background:#eef2f7;border-radius:4px;height:8px;overflow:hidden">' +
        '<div style="height:100%;border-radius:4px;background:'+s.color+';width:'+pct+'%;transition:width .6s"></div>' +
        '</div>' +
        '<span style="font-size:12px;font-weight:700;color:var(--mp-text-1);min-width:24px;text-align:right">'+cnt+'</span>' +
        '<span style="font-size:10px;color:var(--mp-text-3);min-width:32px;text-align:right">'+pct+'%</span>' +
        '</div>';
    }).join('');
  }

  // Analisis rechazos
  if(document.getElementById('rechazosStats')){
    var noInt = d.by_status.no_interesado || 0;
    var optOut = d.by_status.opt_out || 0;
    var totalRech = noInt + optOut;
    var motivos = d.optout_motivos || [];
    var maxMot = motivos.length ? Math.max.apply(null, motivos.map(function(m){return m.total;})) : 1;

    var colores = {
      'Sin interes':'#f23d4f',
      'Sin respuesta':'#fd7e14',
      'Tiene MP':'#009ee3',
      'Precio':'#856404',
      'Otro':'#6c757d'
    };

    var html = '<div style="display:flex;gap:10px;margin-bottom:16px">' +
      '<div style="flex:1;background:#fff5f5;border-radius:10px;padding:12px;text-align:center">' +
      '<div style="font-size:24px;font-weight:800;color:#f23d4f">'+noInt+'</div>' +
      '<div style="font-size:11px;color:#f23d4f;margin-top:2px">No interesados</div></div>' +
      '<div style="flex:1;background:#fff3e0;border-radius:10px;padding:12px;text-align:center">' +
      '<div style="font-size:24px;font-weight:800;color:#fd7e14">'+optOut+'</div>' +
      '<div style="font-size:11px;color:#fd7e14;margin-top:2px">Opt-out</div></div>' +
      '<div style="flex:1;background:#f8f9fa;border-radius:10px;padding:12px;text-align:center">' +
      '<div style="font-size:24px;font-weight:800;color:#6c757d">'+totalRech+'</div>' +
      '<div style="font-size:11px;color:#6c757d;margin-top:2px">Total rechazos</div></div>' +
      '</div>';

    if(motivos.length){
      html += '<div style="font-size:12px;font-weight:600;color:var(--mp-text-2);margin-bottom:10px">Motivos registrados:</div>';
      html += motivos.map(function(m){
        var pct = Math.round(m.total/maxMot*100);
        var color = colores[m.motivo] || '#6c757d';
        return '<div style="margin-bottom:12px">' +
          '<div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px">' +
          '<span style="font-size:12px;font-weight:600;color:var(--mp-text-1)">'+m.motivo+'</span>' +
          '<span style="font-size:11px;background:#f8f9fa;border:1px solid #dee2e6;padding:1px 10px;border-radius:10px;font-weight:700">'+m.total+' casos</span>' +
          '</div>' +
          '<div style="background:#eef2f7;border-radius:6px;height:10px;overflow:hidden">' +
          '<div style="height:100%;border-radius:6px;background:'+color+';width:'+pct+'%;transition:width .6s"></div>' +
          '</div></div>';
      }).join('');

      var acciones = {
        'Sin interes':'Revisar mensaje de prospeccion y pitch inicial',
        'Sin respuesta':'Aumentar seguimientos o probar nuevo horario',
        'Tiene MP':'Pedir referidos — ya conocen el producto',
        'Precio':'Reforzar propuesta de valor y beneficios del POS',
        'Otro':'Revisar notas individuales para identificar patron'
      };
      var topMotivo = motivos[0].motivo;
      html += '<div style="background:#e8f4fd;border-radius:8px;padding:10px 14px;margin-top:4px;font-size:12px;border-left:3px solid #009ee3">' +
        '<strong style="color:#009ee3">Accion sugerida:</strong> ' + (acciones[topMotivo]||'Revisar leads manualmente') + '</div>';
    } else {
      html += '<div style="text-align:center;color:var(--mp-text-3);padding:16px;font-size:12px">Sin rechazos registrados aun</div>';
    }

    document.getElementById('rechazosStats').innerHTML = html;
  }
}'''

if old_charts in content:
    content = content.replace(old_charts, new_charts)
    print("2. Render estados y rechazos OK")
else:
    print("2. No encontrado - buscando...")
    idx = content.find('buildDonutChart')
    print("buildDonutChart pos:", idx)
    print("Contexto:", content[idx:idx+100])

with open('templates/dashboard_test4.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO dashboard_test4")
