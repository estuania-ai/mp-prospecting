with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('id="modalStatus"')
print(content[idx:idx+600])