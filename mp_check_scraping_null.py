with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

lines = content.split('\n')
print("Linea 2351:")
print(lines[2350])
print("\nContexto 2348-2355:")
for i in range(2347, 2355):
    print(f"{i+1}: {lines[i]}")