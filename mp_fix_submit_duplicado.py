with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Eliminar la segunda definicion (la vieja sin opt_out ni cerrado)
idx2 = content.find('async function submitStatus()', 
      content.find('async function submitStatus()') + 1)
end2 = content.find('\n}', idx2) + 2
old_fn2 = content[idx2:end2]
print("Eliminando fn2:", old_fn2[:80])

content = content[:idx2] + content[end2:]

# Verificar
count = content.count('async function submitStatus()')
print("submitStatus definiciones restantes:", count)
print("opt_out en submitStatus:", 'opt_out' in content[content.find('async function submitStatus()'):content.find('async function submitStatus()')+2200])
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test6.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")