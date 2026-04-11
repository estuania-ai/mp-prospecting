with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function runScrapingUrl()')
end = content.find('\n}', idx) + 2
print(content[idx:end])