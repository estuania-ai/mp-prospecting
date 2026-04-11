with open('templates/dashboard_test12.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el card de scraping por URL
idx = content.find('Scraping por link de Google Maps')
end = content.find('</div>\n\n  <div class="card"', idx)
print(content[idx:end+6])