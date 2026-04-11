with open('templates/dashboard_test6.html', 'r', encoding='utf-8') as f:
    content = f.read()

print("proximoEventosList:", content.count('proximoEventosList'))
print("nextSendTime:", content.count('nextSendTime'))
print("checkWaStatus:", 'function checkWaStatus' in content)
print("loadLeads:", 'function loadLeads' in content)
print("updateNextSendTime calls:", content.count('updateNextSendTime'))