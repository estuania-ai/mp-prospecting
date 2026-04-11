with open('app.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Ver rutas actuales
import re
routes = re.findall(r"@app\.route\('([^']+)'\)", content)
print("Rutas actuales:", routes)

# Agregar todas las rutas test al final antes del if __name__
rutas = """
@app.route('/test')
def index_test():
    return render_template('dashboard_test.html')

@app.route('/test2')
def index_test2():
    return render_template('dashboard_test2.html')

@app.route('/test3')
def index_test3():
    return render_template('dashboard_test3.html')

@app.route('/test4')
def index_test4():
    return render_template('dashboard_test4.html')

@app.route('/test5')
def index_test5():
    return render_template('dashboard_test5.html')

@app.route('/test6')
def index_test6():
    return render_template('dashboard_test6.html')

"""

# Insertar antes del if __name__
if "if __name__" in content:
    content = content.replace("if __name__", rutas + "if __name__")
else:
    content += rutas

with open('app.py', 'w', encoding='utf-8') as f:
    f.write(content)

# Verificar
with open('app.py', 'r', encoding='utf-8') as f:
    c = f.read()
routes2 = re.findall(r"@app\.route\('([^']+)'\)", c)
print("Rutas finales:", routes2)
print("LISTO")