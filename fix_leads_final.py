with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix badge no_enviado CSS
if 'badge-no_enviado' not in content:
    content = content.replace(
        '.badge-opt_out{background:#f0f0f0;color:#666}',
        '.badge-opt_out{background:#f0f0f0;color:#666}.badge-no_enviado{background:#f8f9fa;color:#495057;border:1px solid #ced4da;font-weight:600}'
    )
    print("Badge CSS OK")
else:
    print("Badge CSS ya existe")

# 2. Fix statusLabel - agregar no_enviado
if "no_enviado:'No enviado'" not in content:
    content = content.replace(
        "enviado:'Enviado'",
        "no_enviado:'No enviado', enviado:'Enviado'"
    )
    content = content.replace(
        "enviado:'badge-enviado'",
        "no_enviado:'badge-no_enviado', enviado:'badge-enviado'"
    )
    print("StatusLabel OK")
else:
    print("StatusLabel ya existe")

# 3. Fix boton verde -> gris
content = content.replace(
    'class="btn btn-green btn-sm" onclick="openWA(\'${l.phone}\')" title="Abrir WhatsApp">💬</button>',
    'class="btn btn-ghost btn-sm" onclick="openWA(\'${l.phone}\')" title="WhatsApp">💬</button>'
)
print("Boton verde:", 'btn-green btn-sm" onclick="openWA' not in content)

# 4. Agregar openWA si no existe
if 'function openWA' not in content:
    content = content.replace(
        'setInterval(checkWaStatus, 30000);',
        'function openWA(phone){window.location.href="whatsapp://send?phone="+phone.replace(/\\D/g,"");}\n\nsetInterval(checkWaStatus, 30000);'
    )
    print("openWA OK")

# 5. Fix filtro comuna 
content = content.replace(
    'r.map(l=>l.commune).filter(Boolean)',
    'r.map(l=>l.comuna||l.commune).filter(Boolean)'
)
content = content.replace(
    "(!co || l.commune === co)",
    "(!co || (l.comuna||l.commune) === co)"
)
print("Comuna filter OK")

# 6. Fix pills de estado para incluir no_enviado
old_pills = "Object.entries(statusLabel).map(([k,lbl]) =>"
if old_pills in content:
    print("Pills OK - statusLabel ya actualizado")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("\nVerificaciones finales:")
print("badge-no_enviado:", 'badge-no_enviado' in content)
print("no_enviado label:", "no_enviado:'No enviado'" in content)
print("btn verde eliminado:", 'btn-green btn-sm" onclick="openWA' not in content)
print("l.categoria en HTML:", 'l.categoria' in content)
print("l.comuna en HTML:", 'l.comuna||l.commune' in content)
print("LISTO")
