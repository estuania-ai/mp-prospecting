with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar null check antes de cada getElementById que puede fallar
old = "  // Tabla rubros\n  if(d.top_rubros?.length){\n    const maxR = Math.max(...d.top_rubros.map(r=>r.total), 1);\n    document.getElementById('rubrosTable').innerHTML"

new = "  // Tabla rubros\n  if(d.top_rubros?.length && document.getElementById('rubrosTable')){\n    const maxR = Math.max(...d.top_rubros.map(r=>r.total), 1);\n    document.getElementById('rubrosTable').innerHTML"

content = content.replace(old, new)
print("rubrosTable null check:", "rubrosTable'))" in content)

# Agregar null check para categoriasStats
old2 = "  if(d.categoria_stats?.length){\n    const maxCat"
new2 = "  if(d.categoria_stats?.length && document.getElementById('categoriasStats')){\n    const maxCat"
content = content.replace(old2, new2)
print("categoriasStats null check:", "categoriasStats'))" in content)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")