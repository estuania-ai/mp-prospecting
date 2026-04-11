with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar columna Categoria en thead
content = content.replace(
    '<th>Rubro</th>\n          <th>Enviado</th>\n          <th>Estado</th>',
    '<th>Rubro</th>\n          <th>Categoria</th>\n          <th>Estado</th>'
)

# Si ya se elimino Enviado pero falta Categoria
content = content.replace(
    '<th>Rubro</th>\n          <th>Estado</th>',
    '<th>Rubro</th>\n          <th>Categoria</th>\n          <th>Estado</th>'
)

# Agregar td Categoria en la fila, reemplazar td Enviado
content = content.replace(
    '<td>${fmtDate(l.sent_at)}</td>\n      <td>${badge(l.status||',
    '<td><span style="font-size:11px;background:#f0f4f8;color:#4a5568;padding:2px 8px;border-radius:10px">${l.categoria||\'—\'}</span></td>\n      <td>${badge(l.status||'
)

# Corregir commune -> comuna
content = content.replace("l.commune||'—'", "l.comuna||l.commune||'—'")
content = content.replace(
    'r.map(l=>l.commune).filter(Boolean)',
    'r.map(l=>l.comuna||l.commune).filter(Boolean)'
)
content = content.replace(
    "(!co || l.commune === co)",
    "(!co || (l.comuna||l.commune) === co)"
)

# Fix boton verde
content = content.replace(
    'class="btn btn-green btn-sm" onclick="openWA',
    'class="btn btn-ghost btn-sm" onclick="openWA'
)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Verificaciones:")
print("Categoria thead:", 'Categoria' in content)
print("l.categoria td:", 'l.categoria' in content)
print("comuna fix:", 'l.comuna||l.commune' in content)
print("btn verde fix:", 'btn-green btn-sm" onclick="openWA' not in content)
print("LISTO")