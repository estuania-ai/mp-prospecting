with open('templates/dashboard_test10.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar td Proximo msg antes del td de Acciones
old_td = '''          <td class="lead-phone" style="font-size:11px">${(s.ultimo_fidelizacion||'—').slice(0,10)}</td>
          <td>
            <div style="display:flex;gap:4px">
              <button class="btn btn-ghost btn-sm" onclick="openWA('${s.phone}')" title="Abrir chat">💬</button>
              <button class="btn btn-ghost btn-sm" onclick="deleteSeller(${s.id},'${s.name}')">🗑️</button>
            </div>
          </td>'''

new_td = '''          <td class="lead-phone" style="font-size:11px">${(s.ultimo_fidelizacion||'—').slice(0,10)}</td>
          <td style="font-size:11px">
            ${(function(){
              var proximoDia = [7,14,15,30,35].find(function(d){
                var et = (etInfo&&etInfo.etapas||[]).find(function(e){return e.dias===d;});
                return et && et.pendiente;
              });
              if(!proximoDia) return '<span style="color:var(--mp-green);font-size:11px">✓ Ciclo OK</span>';
              var etapaLabel = {7:'Activacion',14:'Potencial',15:'Seguimiento',30:'Gestion',35:'Fidelizacion'}[proximoDia];
              var urgente = dias >= proximoDia;
              return '<span style="background:'+(urgente?'#fff0f0':'#fff3cd')+';color:'+(urgente?'#c0392b':'#856404')+';padding:2px 8px;border-radius:8px;font-weight:600">'+etapaLabel+' (dia '+proximoDia+')</span>';
            })()}
          </td>
          <td>
            <div style="display:flex;gap:4px">
              <button class="btn btn-ghost btn-sm" onclick="openWA(\'${s.phone}\')" title="Abrir chat">💬</button>
              <button class="btn btn-ghost btn-sm" onclick="deleteSeller(${s.id},\'${s.name}\')">🗑️</button>
            </div>
          </td>'''

if old_td in content:
    content = content.replace(old_td, new_td)
    print("TD proximo msg OK")
else:
    print("No encontrado")

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadSellers:", 'function loadSellers' in content)

with open('templates/dashboard_test10.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")