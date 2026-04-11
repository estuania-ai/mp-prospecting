with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('function runScrapingUrl')
end = content.find('\nasync function ', idx+1)
if end == -1:
    end = content.find('\nfunction ', idx+1)
print(content[idx:end])