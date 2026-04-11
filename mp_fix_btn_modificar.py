with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "(!t.completada?'<button onclick=\"completarTareaWidget('+t.id+')\" style=\"background:var(--mp-green);color:#fff;border:none;border-radius:4px;padding:0 4px;cursor:pointer;font-size:9px\">✓</button>':'<span style=\\'color:var(--mp-green)\\'>✓</span>')"

new = "(!t.completada?'<div style=\"display:flex;gap:2px\"><button onclick=\"completarTareaWidget('+t.id+')\" style=\"background:var(--mp-green);color:#fff;border:none;border-radius:4px;padding:0 4px;cursor:pointer;font-size:9px\">✓</button><button onclick=\"abrirReagendar('+t.id+')\" style=\"background:var(--mp-blue);color:#fff;border:none;border-radius:4px;padding:0 4px;cursor:pointer;font-size:9px\">✎</button></div>':'<span style=\\'color:var(--mp-green)\\'>✓</span>')"

if old in content:
    content = content.replace(old, new)
    print("Boton modificar OK")
else:
    print("No encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test7.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")