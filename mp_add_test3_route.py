with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test3' not in content:
    content = content.replace(
        "@app.route('/test2')\ndef index_test2():\n    return render_template('dashboard_test2.html')",
        "@app.route('/test2')\ndef index_test2():\n    return render_template('dashboard_test2.html')\n\n@app.route('/test3')\ndef index_test3():\n    return render_template('dashboard_test3.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test3 agregada OK")
else:
    print("Ya existe")