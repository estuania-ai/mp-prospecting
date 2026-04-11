with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

count = content.count('async function submitStatus')
print("submitStatus definiciones:", count)

count2 = content.count('function onStatusChange')
print("onStatusChange definiciones:", count2)

idx = content.find('id="modalStatus"')
end = content.find('</div>\n\n<div class="modal', idx)
print("\nModal status HTML:")
print(content[idx:end+6])