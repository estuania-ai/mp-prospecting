with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar que textos existen
print("commune en loadOverview:", content.count('c.commune'))
print("weekly_sends en JS:", 'weekly_sends' in content)
print("comunasList en HTML:", 'comunasList' in content)
print("chartWeekly en HTML:", 'chartWeekly' in content)

# Fix 1: c.commune -> c.comuna en comunasList
if "c.commune" in content:
    content = content.replace("c.commune", "c.comuna||c.commune")
    print("Fix commune OK")

# Fix 2: verificar buildWeeklyChart recibe datos
idx = content.find('buildWeeklyChart(')
print("\nbuildWeeklyChart llamada:", content[idx:idx+50])

# Fix 3: verificar que weekly tiene campo 'week'
idx2 = content.find("'Sem '+w.week")
print("weekly label:", content[idx2:idx2+50] if idx2>0 else "NO ENCONTRADO")

# Si no tiene el label correcto, arreglarlo
if idx2 == -1:
    idx3 = content.find("w => 'Sem")
    print("alternativa:", content[idx3:idx3+60] if idx3>0 else "NO ENCONTRADO")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("\nOK guardado")