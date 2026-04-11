with open('templates/dashboard_test4.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadEnvios:", 'function loadEnvios' in content)
print("setInterval:", 'setInterval(checkWaStatus' in content)
print("Tamanio archivo:", len(content))

# Ver los ultimos 200 chars
print("\nFinal del archivo:")
print(repr(content[-200:]))