with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''</div>\n      </div>\n    </div>\n    <div class="card">\n      <div class="card-title"><span class="card-icon">📋</span>Configuración de envío</div>'''

new = '''</div>
      </div>
      <div style="border-top:1px solid var(--mp-border);margin-top:8px;padding-top:8px">
        <div style="font-size:11px;font-weight:600;color:var(--mp-text-2);margin-bottom:6px">📋 Tareas de prospectos hoy</div>
        <div id="tareasHoyEnvios">
          <div style="font-size:11px;color:var(--mp-text-3);text-align:center;padding:6px">Sin tareas para hoy</div>
        </div>
      </div>
    </div>
    <div class="card">
      <div class="card-title"><span class="card-icon">📋</span>Configuración de envío</div>'''

if old in content:
    content = content.replace(old, new)
    print("OK")
else:
    idx = content.find('Configuración de envío')
    print("Texto exacto antes:")
    print(repr(content[idx-150:idx]))

print("tareasHoyEnvios:", 'tareasHoyEnvios' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")