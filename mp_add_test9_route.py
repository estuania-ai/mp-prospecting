with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test9' not in content:
    content = content.replace(
        "@app.route('/test8')\ndef index_test8():\n    return render_template('dashboard_test8.html')",
        "@app.route('/test8')\ndef index_test8():\n    return render_template('dashboard_test8.html')\n\n@app.route('/test9')\ndef index_test9():\n    return render_template('dashboard_test9.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test9 agregada OK")
else:
    print("Ya existe")