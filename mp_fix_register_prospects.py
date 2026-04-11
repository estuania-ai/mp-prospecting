with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("register prospects:", 'prospects_bp' in content)
# Buscar donde se registran los blueprints
idx = content.find('register_blueprint')
print("Contexto registros:")
while idx > 0:
    print(content[idx:idx+80])
    idx = content.find('register_blueprint', idx+1)

# Agregar registro si no existe
if "register_blueprint(prospects_bp" not in content:
    content = content.replace(
        "app.register_blueprint(leads_bp, url_prefix='/api/leads')",
        "app.register_blueprint(leads_bp, url_prefix='/api/leads')\napp.register_blueprint(prospects_bp, url_prefix='/api/prospects')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Blueprint prospects registrado OK")
else:
    print("Ya registrado")