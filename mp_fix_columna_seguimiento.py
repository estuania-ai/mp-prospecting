with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Agregar columna en thead
old_thead = '<th>Estado</th>\n          <th>Acciones</th>'
new_thead = '<th>Estado</th>\n          <th>Seguimiento</th>\n          <th>Acciones</th>'
content = content.replace(old_thead, new_thead)
print("Thead OK:", 'Seguimiento' in content)

# 2. Agregar td en cada fila antes de acciones
old_td = "      <td>${badge(l.status||'enviado')}</td>\n      <td>\n        <div style=\"display:flex;gap:4px\">"
new_td = """      <td>${badge(l.status||'enviado')}</td>
      <td>
        ${l.seguimiento_tipo ? '<span style="font-size:11px;padding:2px 8px;border-radius:10px;background:#fff3cd;color:#856404;font-weight:600">🔔 ' + (l.seguimiento_tipo==='seguimiento_24h'?'24h enviado':l.seguimiento_tipo==='seguimiento_72h'?'72h enviado':'Enviado') + '</span>' : '<span style="font-size:11px;color:var(--mp-text-3)">—</span>'}
      </td>
      <td>
        <div style="display:flex;gap:4px">"""
content = content.replace(old_td, new_td)
print("TD seguimiento OK:", 'seguimiento_tipo' in content)

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")