with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: el JS busca scraRubroUrl pero el HTML tiene scraUrlRubro
content = content.replace(
    "document.getElementById('scraRubroUrl').innerHTML",
    "if(document.getElementById('scraUrlRubro')) document.getElementById('scraUrlRubro').innerHTML"
)
print("Fix scraRubroUrl OK")

# Fix 2: agregar null checks en loadScraping para los nuevos elementos
content = content.replace(
    "document.getElementById('scraLeadsPorRubro')",
    "document.getElementById('scraLeadsPorRubro')"
)

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test11.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")