with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar que el widget HTML ya es el nuevo
print("Widget gradiente OK:", 'linear-gradient(135deg,#009ee3' in content)
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)
print("loadOverview:", 'function loadOverview' in content)
print("renderLeads:", 'function renderLeads' in content)
print("loadInteresados:", 'function loadInteresados' in content)
print()
print("Tamanio archivo:", len(content))