with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Verificar funcion toast
idx = content.find('function toast(')
print("Toast funcion:", content[idx:idx+200])
print()
# Verificar elemento toast en HTML
print("toast-msg en HTML:", 'id="toast-msg"' in content)
print("toast en HTML:", 'id="toast"' in content)
print("snackbar en HTML:", 'id="snackbar"' in content)