with open('templates/dashboard_test8.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find("var rubrosValidos = ['almacen'")
end = content.find('];', idx) + 2
print("Texto completo:")
print(repr(content[idx:end+50]))