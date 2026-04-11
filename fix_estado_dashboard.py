with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

content = content.replace(
    "enviado:'Enviado'",
    "no_enviado:'No enviado', enviado:'Enviado'"
)
content = content.replace(
    "enviado:'badge-enviado'",
    "no_enviado:'badge-no-enviado', enviado:'badge-enviado'"
)
content = content.replace(
    '.badge-enviado{background:#e8f4fd;color:#0078c8}',
    '.badge-no-enviado{background:#f8f9fa;color:#495057;border:1px solid #dee2e6}.badge-enviado{background:#e8f4fd;color:#0078c8}'
)
content = content.replace(
    '<option value="enviado">Enviado</option>',
    '<option value="no_enviado">No enviado</option>\n      <option value="enviado">Enviado</option>'
)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK dashboard actualizado')