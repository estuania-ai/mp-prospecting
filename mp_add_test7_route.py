with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test7' not in content:
    content = content.replace(
        "@app.route('/test6')\ndef index_test6():\n    return render_template('dashboard_test6.html')",
        "@app.route('/test6')\ndef index_test6():\n    return render_template('dashboard_test6.html')\n\n@app.route('/test7')\ndef index_test7():\n    return render_template('dashboard_test7.html')"
    )
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test7 agregada OK")
else:
    print("Ya existe")