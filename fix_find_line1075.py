with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    lines = f.readlines()

# Mostrar lineas alrededor de 1075
start = max(0, 1070)
end = min(len(lines), 1080)
for i, line in enumerate(lines[start:end], start+1):
    print(f"{i}: {line.rstrip()}")