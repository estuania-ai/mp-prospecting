with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test2' not in content:
    content = content.replace(
        "@app.route('/test')\ndef index_test():\n    return render_template('dashboard_test.html')",
        "@app.route('/test')\ndef index_test():\n    return render_template('dashboard_test.html')\n\n@app.route('/test2')\ndef index_test2():\n    return render_template('dashboard_test2.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test2 agregada OK")
else:
    print("Ya existe")