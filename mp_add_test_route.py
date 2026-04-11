with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

if 'dashboard_test' not in content:
    old = "@app.route('/')\ndef index():\n    return render_template('dashboard.html')"
    new = "@app.route('/')\ndef index():\n    return render_template('dashboard.html')\n\n@app.route('/test')\ndef index_test():\n    return render_template('dashboard_test.html')"
    content = content.replace(old, new)
    with open('app.py', 'w', encoding='utf-8') as f:
        f.write(content)
    print("Ruta /test agregada OK")
else:
    print("Ya existe")
