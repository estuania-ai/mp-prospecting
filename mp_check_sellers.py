with open('templates/dashboard_test10.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Ver thead de sellers
idx = content.find('sellersBody')
start = content.rfind('<thead>', 0, idx)
end = content.find('</thead>', start) + 8
print("=== THEAD sellers ===")
print(content[start:end])
print()

# Ver renderizado de cada fila
idx2 = content.find('function loadSellers')
end2 = content.find('\nasync function ', idx2+1)
print("=== loadSellers largo:", end2-idx2, "chars ===")
print("Tiene sellersBody:", 'sellersBody' in content[idx2:end2])