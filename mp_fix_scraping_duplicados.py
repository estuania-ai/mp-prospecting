with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Eliminar card con chartRubros (el original vacio)
old_rubros = '''<div class="card">
      <div class="card-title"><span class="card-icon">📊</span>Leads por rubro</div>
      <div class="chart-wrap chart-h240"><canvas id="chartRubros"></canvas></div>
    </div>'''

if old_rubros in content:
    content = content.replace(old_rubros, '')
    print("Card chartRubros eliminado OK")
else:
    # Buscar variante
    idx = content.find('chartRubros')
    start = content.rfind('<div class="card">', 0, idx)
    end = content.find('</div>\n    </div>', idx) + 16
    print("Variante encontrada:")
    print(repr(content[start:end]))

# Eliminar card con scraComunes (el original vacio de comunas)
old_comunas = content.find('scraComunes')
if old_comunas > 0:
    start = content.rfind('<div class="card">', 0, old_comunas)
    end = content.find('</div>\n    </div>', old_comunas) + 16
    old_card = content[start:end]
    print("Card scraComunes encontrado:")
    print(repr(old_card[:100]))
    content = content[:start] + content[end:]
    print("Card scraComunes eliminado OK")

print("chartRubros queda:", 'chartRubros' in content)
print("scraComunes queda:", 'scraComunes' in content)
print("scraLeadsPorRubro queda:", 'scraLeadsPorRubro' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)

with open('templates/dashboard_test11.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")