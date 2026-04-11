with open('jobs/send_prospecting.py', 'r', encoding='utf-8') as f:
    content = f.read()

old = '''def build_message(contact: dict) -> str:
    nombre    = contact.get('name', 'estimado/a')
    rubro_key = contact.get('rubro', 'almacen')
    return get_mensaje(rubro_key, nombre)'''

new = '''def build_message(contact: dict) -> str:
    nombre    = contact.get('name', 'estimado/a')
    rubro_key = contact.get('rubro', 'almacen')
    comuna    = contact.get('comuna', '')
    return get_mensaje(rubro_key, nombre, comuna)'''

content = content.replace(old, new)

with open('jobs/send_prospecting.py', 'w', encoding='utf-8') as f:
    f.write(content)
print('OK - comuna agregada al mensaje')