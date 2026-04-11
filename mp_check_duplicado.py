with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    content = f.read()

count = content.count('async function submitStatus()')
print(f"submitStatus aparece {count} veces")

idx = 0
for i in range(count):
    idx = content.find('async function submitStatus()', idx)
    print(f"  Ocurrencia {i+1} en pos: {idx}")
    idx += 1