with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Contar todas las referencias a commune
count = content.count('commune')
print(f"Referencias a 'commune' restantes: {count}")

# Mostrar contexto de cada una
idx = 0
while True:
    idx = content.find('commune', idx)
    if idx == -1:
        break
    print(f"  pos {idx}: {content[idx-30:idx+40]}")
    idx += 1

# Reemplazar todas
content = content.replace('.commune', '.comuna')
content = content.replace("['commune']", "['comuna']")
content = content.replace('"commune"', '"comuna"')

print(f"\nReferencias restantes despues del fix: {content.count('commune')}")

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print("OK")