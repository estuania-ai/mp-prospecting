with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Elementos que loadOverview intenta usar
elementos = [
    'overviewDate', 'kpi-leads', 'kpi-sent', 'kpi-apertura', 'kpi-apertura-sub',
    'kpi-interesados', 'kpi-interes-pct', 'kpi-reuniones', 'kpi-cerrados',
    'kpi-cierre-pct', 'kpi-no', 'kpi-sellers', 'badgeSellers',
    'funnelChart', 'comunasList', 'chartWeekly', 'chartDonut', 'donutLegend',
    'rubrosTable', 'categoriasStats'
]

print("Elementos faltantes en HTML:")
faltantes = []
for el in elementos:
    if f'id="{el}"' not in content:
        print(f"  FALTA: {el}")
        faltantes.append(el)

if not faltantes:
    print("  Todos existen")