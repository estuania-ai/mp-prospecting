with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test4' not in content:
    content = content.replace(
        "@app.route('/test3')\ndef index_test3():\n    return render_template('dashboard_test3.html')",
        "@app.route('/test3')\ndef index_test3():\n    return render_template('dashboard_test3.html')\n\n@app.route('/test4')\ndef index_test4():\n    return render_template('dashboard_test4.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test4 agregada OK")
else:
    print("Ya existe")