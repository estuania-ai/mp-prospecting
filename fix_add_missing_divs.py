with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar rubrosTable antes del card de comunas
old_comunas = '<div class="card-title"><span class="card-icon">🏙️</span>Top comunas</div>'

new_rubros_y_comunas = '''<div class="card-title"><span class="card-icon">📊</span>Rubros prospectados y tasa de respuesta</div>
    <div class="table-wrap" style="border-radius:8px;max-height:220px;overflow-y:auto">
      <table>
        <thead><tr>
          <th>Rubro</th>
          <th style="text-align:center">Leads</th>
          <th style="text-align:center">Interesados</th>
          <th style="text-align:center">Cerrados</th>
          <th style="text-align:center">Tasa</th>
        </tr></thead>
        <tbody id="rubrosTable"></tbody>
      </table>
    </div>
  </div>

  <div class="card">
    <div class="card-title"><span class="card-icon">🏙️</span>Top comunas</div>'''

content = content.replace(old_comunas, new_rubros_y_comunas)
print("rubrosTable agregado:", 'rubrosTable' in content)

# Agregar categoriasStats - buscar donde insertar (despues de comunasList)
old_comunas_end = '<div class="commune-list" id="comunasList">'
new_comunas_end = '''<div class="commune-list" id="comunasList">
      </div>
    </div>

    <div class="card">
      <div class="card-title"><span class="card-icon">📦</span>Leads por categoria</div>
      <div id="categoriasStats" style="display:flex;flex-direction:column;gap:6px;max-height:200px;overflow-y:auto">'''

content = content.replace(old_comunas_end, new_comunas_end)
print("categoriasStats agregado:", 'categoriasStats' in content)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK guardado")