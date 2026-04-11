with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test8' not in content:
    content = content.replace(
        "@app.route('/test7')\ndef index_test7():\n    return render_template('dashboard_test7.html')",
        "@app.route('/test7')\ndef index_test7():\n    return render_template('dashboard_test7.html')\n\n@app.route('/test8')\ndef index_test8():\n    return render_template('dashboard_test8.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test8 agregada OK")
else:
    print("Ya existe")