with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

print("test5 route existe:", 'test5' in content)
print("test6 route existe:", 'test6' in content)

if 'test6' not in content:
    # Buscar ultima ruta de test
    idx = content.rfind("render_template('dashboard_test")
    end = content.find('\n', idx)
    print("Ultima ruta test:", content[idx:end])
    
    content = content.replace(
        "render_template('dashboard_test5.html')",
        "render_template('dashboard_test5.html')\n\n@app.route('/test6')\ndef index_test6():\n    return render_template('dashboard_test6.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test6 agregada OK")
else:
    print("Ya existe")

# Verificar
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()
print("Verificacion test6:", 'test6' in c)