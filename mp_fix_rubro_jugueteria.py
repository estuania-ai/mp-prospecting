"""
mp_fix_rubro_jugueteria.py
Cambia label de bazar a Jugueteria/Regalos en todos los selects del dashboard
"""
with open('templates/dashboard_test10.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Cambiar en todos los selects donde aparece bazar
replacements = [
    ('<option value="bazar">Bazar</option>', '<option value="bazar">Jugueteria / Regalos</option>'),
    ('<option value="bazar">Bazar / Jugueteria</option>', '<option value="bazar">Jugueteria / Regalos</option>'),
]

for old, new in replacements:
    if old in content:
        content = content.replace(old, new)
        print(f"OK: {old[:40]} -> {new[:40]}")

# Cambiar en RUBRO_CAT del JS
content = content.replace(
    "'bazar':'Retail Especializado y Hogar'",
    "'bazar':'Retail Especializado y Hogar','jugueteria':'Retail Especializado y Hogar','regalos':'Retail Especializado y Hogar'"
)

# Cambiar en normalizarRubro
if 'jugueteria' not in content:
    content = content.replace(
        "'bazar':'bazar'",
        "'bazar':'bazar','jugueteria':'bazar','juguetería':'bazar','regalos':'bazar'"
    )

print("Jugueteria en selects:", content.count('Jugueteria / Regalos'))
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)

with open('templates/dashboard_test10.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")
