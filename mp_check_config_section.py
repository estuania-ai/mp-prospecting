with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('page-config')
end = content.find('<!-- ─── ', idx+100)
print(content[idx:idx+2000])