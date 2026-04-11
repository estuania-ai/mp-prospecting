with open('templates/dashboard_test7.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar renderCalendario
idx = content.find('function renderCalendario')
end = content.find('\nfunction ', idx+1)
print(content[idx:end])