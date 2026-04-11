with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = """          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},'${l.status||'enviado'}')">✏️</button>
          <a href="https://wa.me/${l.phone?.replace(/\\D/g,'')}" target="_blank" class="btn btn-green btn-sm">💬</a>"""

new = """          <button class="btn btn-ghost btn-sm" onclick="openStatusModal(${l.id},'${l.status||'enviado'}')">✏️</button>
          <a href="https://wa.me/${l.phone?.replace(/\\D/g,'')}" target="_blank" class="btn btn-green btn-sm">💬</a>
          ${l.status==='enviado' ? '<button class="btn btn-ghost btn-sm" onclick="sendSeguimiento('+l.id+',\\''+l.name+'\')" title="Enviar seguimiento" style="color:#856404;font-size:12px">🔔</button>' : ''}"""

if old in content:
    content = content.replace(old, new)
    print("Boton agregado OK")
else:
    print("Texto no encontrado - buscando...")
    idx = content.find("openStatusModal(${l.id}")
    print("Texto exacto:", repr(content[idx:idx+200]))

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")