with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Cargar rubros personalizados desde BD al iniciar
old_init = '// ─── INIT ────────────────────────────────────────────\nloadOverview();\ncheckWaStatus();\nupdateNextSendTime();'

new_init = '''// ─── INIT ────────────────────────────────────────────
window.rubrosPersonalizados = [];
api('/api/leads/rubros-personalizados').then(function(r){
  if(r && r.rubros) window.rubrosPersonalizados = r.rubros;
});
loadOverview();
checkWaStatus();
updateNextSendTime();'''

if old_init in content:
    content = content.replace(old_init, new_init)
    print("Init rubros OK")
else:
    print("No encontrado - buscando...")
    idx = content.find('loadOverview();')
    print("Contexto:", repr(content[idx-60:idx+60]))

print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test8.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")