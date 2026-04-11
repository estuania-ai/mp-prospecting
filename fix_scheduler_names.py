with open('templates/dashboard.html', 'r', encoding='utf-8') as f:
    content = f.read()

old = "j.id === 'prospecting_daily' ? 'Prospección L-V (09:30 · 15:00 · 17:30)' : 'Fidelización Lunes 11:00 AM'"

new = """(j.id === 'batch_0930' ? 'Prospeccion 09:30 AM - 15 mensajes' :
         j.id === 'batch_1500' ? 'Prospeccion 15:00 PM - 10 mensajes' :
         j.id === 'batch_1730' ? 'Prospeccion 17:30 PM - 15 mensajes' :
         j.id === 'fidelizacion_weekly' ? 'Fidelizacion Sellers - Lunes 11:00 AM' :
         j.id)"""

content = content.replace(old, new)

with open('templates/dashboard.html', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - nombres corregidos')