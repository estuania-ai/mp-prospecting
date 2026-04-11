with open('apify_scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar scrape_from_url
idx = content.find('def scrape_from_url')
end = content.find('\n    def ', idx+1)
print(content[idx:end])