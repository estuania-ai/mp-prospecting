with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "  if(r && r.ok){ toast('Estado actualizado','success'); closeModal('modalStatus'); loadLeads(); }\n  else toast('Error actualizando estado','error');\n}"

new = """  if(r && r.ok){
    toast('Estado actualizado','success');
    closeModal('modalStatus');
    loadLeads();
    if(status === 'interesado'){
      var lead = (allLeads||[]).find(function(l){return String(l.id)===String(id);});
      if(lead){
        api('/api/prospects/',{method:'POST',body:JSON.stringify({
          lead_id:lead.id, name:lead.name, phone:lead.phone,
          negocio:lead.name, rubro:lead.rubro||'', categoria:lead.categoria||'',
          comuna:lead.comuna||lead.commune||'', procedencia:'Online'
        })}).then(function(r2){
          if(r2&&r2.ok) toast('Prospecto agregado a Interesados','success');
        });
      }
    }
  }
  else toast('Error actualizando estado','error');
}"""

if old in content:
    content = content.replace(old, new)
    print("Auto-crear OK")
else:
    print("No encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")