with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Mejorar columna seguimiento con iconos visuales
old_td_seg = """      <td>
        ${l.seguimiento_tipo ? '<span style="font-size:11px;padding:2px 8px;border-radius:10px;background:#fff3cd;color:#856404;font-weight:600">🔔 ' + (l.seguimiento_tipo==='seguimiento_24h'?'24h enviado':l.seguimiento_tipo==='seguimiento_72h'?'72h enviado':'Enviado') + '</span>' : '<span style="font-size:11px;color:var(--mp-text-3)">—</span>'}
      </td>"""

new_td_seg = """      <td style="text-align:center">
        ${(function(){
          var s24 = l.seguimiento_24h;
          var s72 = l.seguimiento_72h;
          if(s24 && s72) return '<span title="2 seguimientos enviados (24h y 72h)" style="font-size:16px;letter-spacing:2px">🟡🟡</span>';
          if(s72) return '<span title="Seguimiento 72h enviado el '+l.seguimiento_72h_fecha+'" style="font-size:16px">🟡</span><span style="font-size:10px;color:#856404;display:block">72h</span>';
          if(s24) return '<span title="Seguimiento 24h enviado el '+l.seguimiento_24h_fecha+'" style="font-size:16px">🟡</span><span style="font-size:10px;color:#856404;display:block">24h</span>';
          return '<span style="font-size:13px;color:var(--mp-text-3)">—</span>';
        })()}
      </td>"""

content = content.replace(old_td_seg, new_td_seg)
print("Iconos seguimiento OK:", '🟡🟡' in content)

# 2. Actualizar boton 🔔 - solo si estado es enviado Y no tiene 72h (max 2 seguimientos)
old_btn = """          ${l.status==='enviado' ? `<button class="btn btn-ghost btn-sm" onclick="sendSeguimiento(${l.id},'${l.name.replace(/'/g,'')}')" title="Seguimiento 24h/72h" style="color:#856404">🔔</button>` : ''}"""

new_btn = """          ${(l.status==='enviado' && !l.seguimiento_72h) ? `<button class="btn btn-ghost btn-sm" onclick="sendSeguimiento(${l.id},'${l.name.replace(/'/g,'')}')" title="${l.seguimiento_24h?'Enviar seguimiento 72h':'Enviar seguimiento 24h'}" style="color:#856404">🔔</button>` : ''}"""

content = content.replace(old_btn, new_btn)
print("Boton regla OK:", 'seguimiento_72h' in content)

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO dashboard")