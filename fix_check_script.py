with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

# Buscar todos los tags script
import re
scripts = [(m.start(), m.group()) for m in re.finditer(r'<script', content)]
print(f'Total tags script: {len(scripts)}')
for pos, tag in scripts:
    print(f'  pos:{pos} -> {content[pos:pos+50]}')

# Ver el final del archivo
print('\nUltimos 500 chars:')
print(content[-500:])