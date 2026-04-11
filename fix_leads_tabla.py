with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Badge no_enviado en CSS
content = content.replace(
    '.badge-opt_out{background:#f0f0f0;color:#666}',
    '.badge-opt_out{background:#f0f0f0;color:#666}.badge-no_enviado{background:#f8f9fa;color:#495057;border:1px solid #ced4da;font-weight:600}'
)

# 2. Agregar no_enviado a statusLabel
content = content.replace(
    "enviado:'Enviado'",
    "no_enviado:'No enviado', enviado:'Enviado'"
)
content = content.replace(
    "enviado:'badge-enviado'",
    "no_enviado:'badge-no_enviado', enviado:'badge-enviado'"
)

# 3. Header tabla: eliminar Enviado, agregar Categoria
content = content.replace(
    '<th>Rubro</th>\n          <th>Enviado</th>\n          <th>Estado</th>',
    '<th>Rubro</th>\n          <th>Categoria</th>\n          <th>Estado</th>'
)

# 4. Fila tabla: eliminar col Enviado, agregar Categoria, corregir commune->comuna
old_row = """      <td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">${l.rubro||'—'}</span></td>
      <td>${fmtDate(l.sent_at)}</td>
      <td>${badge(l.status||'enviado')}</td>"""

new_row = """      <td><span style="font-size:11px;background:var(--mp-blue-lt);color:var(--mp-blue);padding:2px 8px;border-radius:10px">${l.rubro||'—'}</span></td>
      <td><span style="font-size:11px;background:#f0f4f8;color:#4a5568;padding:2px 8px;border-radius:10px">${l.categoria||'—'}</span></td>
      <td>${badge(l.status||'no_enviado')}</td>"""

content = content.replace(old_row, new_row)

# 5. Corregir commune -> comuna en filtros
content = content.replace(
    "r.map(l=>l.commune).filter(Boolean)",
    "r.map(l=>l.comuna||l.commune).filter(Boolean)"
)
content = content.replace(
    "l.commune === co",
    "(l.comuna||l.commune) === co"
)

# 6. Corregir td de comuna en fila
content = content.replace(
    "<td>${l.commune||'—'}</td>",
    "<td>${l.comuna||l.commune||'—'}</td>"
)

# 7. Boton WA usar openWA
content = content.replace(
    'target="_blank" class="btn btn-green btn-sm">💬</a>',
    'class="btn btn-green btn-sm" onclick="openWA(\'${l.phone}\')">💬</button>'
)

# 8. Agregar funcion openWA si no existe
if 'function openWA' not in content:
    content = content.replace(
        'setInterval(checkWaStatus, 30000);',
        'function openWA(phone){window.location.href="whatsapp://send?phone="+phone.replace(/\\D/g,"");}\n\nsetInterval(checkWaStatus, 30000);'
    )

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Verificaciones:")
print("badge-no_enviado:", 'badge-no_enviado' in content)
print("Categoria col:", 'Categoria' in content)
print("l.categoria:", 'l.categoria' in content)
print("comuna fix:", 'l.comuna||l.commune' in content)
print("openWA:", 'openWA' in content)
print("LISTO")