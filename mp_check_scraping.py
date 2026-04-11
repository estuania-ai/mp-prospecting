with open('templates/dashboard_test11.html', 'r', encoding='utf-8') as f:
    content = f.read()

idx = content.find('page-scraping')
end = content.find('<!-- ─── INTEL', idx)
if end == -1:
    end = content.find('<!-- ─── CONFIG', idx)
print("Scraping page:")
print(content[idx:idx+1000])