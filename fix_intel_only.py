with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Nav
if 'Inteligencia' not in content:
    content = content.replace(
        'onclick="showPage(\'config\'',
        'onclick="showPage(\'intel\',this,\'Inteligencia\')"><span class="nav-icon">*</span> Inteligencia</div>\n  <div class="nav-item" onclick="showPage(\'config\''
    )
    print("Nav OK")
else:
    print("Nav ya existe")

# Loader
if 'intel: loadIntel' not in content:
    content = content.replace('config: loadConfig,', 'config: loadConfig,\n    intel: loadIntel,')
    print("Loader OK")
else:
    print("Loader ya existe")

# JS
if 'function loadIntel' not in content:
    js = "\nasync function loadIntel(){var s=await api('/api/intel/suggestions');var n=await api('/api/intel/next-searches');if(!s)return;document.getElementById('intel-rubros-con').textContent=s.resumen.total_rubros_con_leads;document.getElementById('intel-rubros-sin').textContent=s.resumen.total_rubros_sin_leads;document.getElementById('intel-comunas').textContent=s.resumen.comunas_cubiertas;document.getElementById('intel-sugerencias').textContent=s.resumen.sugerencias_pendientes;document.getElementById('intelRubrosTable').innerHTML=s.rubro_stats.map(function(r){var tasa=r.enviados>0?Math.round(r.interesados/r.enviados*100):0;var pri,pc,pb;if(tasa>=15){pri='ALTA';pc='#155724';pb='#d4edda';}else if(tasa>=5){pri='MEDIA';pc='#856404';pb='#fff3cd';}else if(r.pendientes>0){pri='NORMAL';pc='#0c5460';pb='#d1ecf1';}else{pri='BAJA';pc='#6c757d';pb='#f8f9fa';}return '<tr><td><span style=\"background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px;font-size:11px\">'+r.rubro+'</span></td><td>'+r.total_leads+'</td><td>'+r.enviados+'</td><td style=\"color:var(--mp-warn);font-weight:600\">'+r.interesados+'</td><td style=\"font-weight:700;color:'+(tasa>=10?'var(--mp-green)':'var(--mp-text-3)')+'\">'+tasa+'%</td><td><span style=\"padding:2px 8px;border-radius:10px;font-size:11px;font-weight:600;background:'+pb+';color:'+pc+'\">'+pri+'</span></td></tr>';}).join('')||'<tr><td colspan=\"6\" style=\"text-align:center;padding:20px;color:var(--mp-text-3)\">Sin datos aun</td></tr>';var maxC=Math.max.apply(null,s.comuna_stats.map(function(c){return c.total_leads;}));if(maxC<=0)maxC=1;document.getElementById('intelComunas').innerHTML=s.comuna_stats.length?s.comuna_stats.map(function(c){var tasa=c.total_leads>0?Math.round((c.interesados||0)/c.total_leads*100):0;return '<div class=\"commune-row\"><div class=\"commune-name\">'+c.comuna+'</div><div class=\"commune-track\"><div class=\"commune-bar\" style=\"width:'+Math.round(c.total_leads/maxC*100)+'%\"></div></div><div class=\"commune-val\">'+c.total_leads+'</div>'+(tasa>0?'<span style=\"margin-left:8px;font-size:11px;font-weight:700;color:var(--mp-warn)\">'+tasa+'%</span>':'')+'</div>';}).join(''):'Sin datos';document.getElementById('intelSuggestions').innerHTML=s.suggestions.length?s.suggestions.map(function(sg){return '<div class=\"log-item\"><div class=\"log-info\"><div class=\"log-title\">'+sg.mensaje+'</div><div class=\"log-meta\">'+sg.query_sugerida+'</div></div><span class=\"badge '+(sg.prioridad==='alta'?'badge-no':'badge-interesado')+'\">'+sg.prioridad+'</span></div>';}).join(''):'<div style=\"color:var(--mp-text-3);padding:20px;text-align:center\">Base bien cubierta</div>';document.getElementById('nextSearches').innerHTML=n&&n.next_searches&&n.next_searches.length?n.next_searches.slice(0,8).map(function(x){return '<div class=\"log-item\"><div class=\"log-info\"><div class=\"log-title\">'+x.rubro_label+' en '+x.comuna+'</div><div class=\"log-meta\">'+x.razon+'</div></div><a href=\"'+x.maps_url_base+'\" target=\"_blank\" class=\"btn btn-ghost btn-sm\">Maps</a></div>';}).join(''):'<div style=\"color:var(--mp-text-3);padding:20px;text-align:center\">Agrega leads para ver recomendaciones</div>';document.getElementById('intelRubrosSin').innerHTML=s.rubros_sin_leads.length?s.rubros_sin_leads.map(function(r){return '<span style=\"display:inline-flex;align-items:center;gap:4px;padding:6px 12px;border-radius:20px;background:#fff3e0;color:#e65100;font-size:12px;font-weight:600;border:1px solid #ffcc80\">'+r.emoji+' '+r.label+'</span>';}).join(''):'<span style=\"color:var(--mp-text-3)\">Todos los rubros tienen leads</span>';}\n"
    content = content.replace('setInterval(checkWaStatus, 30000);', js + 'setInterval(checkWaStatus, 30000);')
    print("JS OK")
else:
    print("JS ya existe")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")