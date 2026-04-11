with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Agregar elemento toast antes del cierre del body
if 'id="toast"' not in content:
    content = content.replace(
        '</body>',
        '<div id="toast" class="toast"></div>\n</body>'
    )
    print("Toast HTML agregado OK")
else:
    print("Ya existe")

with open('templates/dashboard_test.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("LISTO")