with open('apify_scraper.py', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar el actor ID
import re
# Buscar patrones como actor IDs
patterns = ['actor', 'Actor', 'ACT_', 'acts/']
for p in patterns:
    idx = content.find(p)
    while idx > 0:
        print(f"'{p}' en pos {idx}:", repr(content[idx:idx+80]))
        idx = content.find(p, idx+1)
        if idx > 5000:
            break