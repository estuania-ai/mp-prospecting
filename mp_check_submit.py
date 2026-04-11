with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar submitStatus completo
idx = content.find('async function submitStatus()')
end = content.find('\nfunction openStatusModal', idx)
print(content[idx:end])