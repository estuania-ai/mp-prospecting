with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test5' not in content:
    content = content.replace(
        "@app.route('/test4')\ndef index_test4():\n    return render_template('dashboard_test4.html')",
        "@app.route('/test4')\ndef index_test4():\n    return render_template('dashboard_test4.html')\n\n@app.route('/test5')\ndef index_test5():\n    return render_template('dashboard_test5.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test5 agregada OK")
else:
    print("Ya existe")