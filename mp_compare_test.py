with open('templates/dashboard_test.html', 'r', encoding='utf-8') as f:
    test1 = f.read()

with open('templates/dashboard_test2.html', 'r', encoding='utf-8') as f:
    test2 = f.read()

print(f"Tamanio test:  {len(test1)} chars")
print(f"Tamanio test2: {len(test2)} chars")
print()

features = [
    ('Modal cerrado con contacto',  'cerradoContacto'),
    ('Modal optout con motivos',    'optoutMotivo'),
    ('Boton seguimiento',           'sendSeguimiento'),
    ('Columna seguimiento',         'seguimiento_24h'),
    ('Inteligencia nav',            'page-intel'),
    ('Scheduler batch_0930',        'batch_0930'),
    ('Rubros prospectados',         'rubrosTable'),
    ('Categorias stats',            'categoriasStats'),
    ('Badge no_enviado',            'badge-no_enviado'),
    ('Columna Categoria leads',     'l.categoria'),
    ('Toast elemento HTML',         'id="toast"'),
    ('onStatusChange',              'function onStatusChange'),
    ('submitStatus completo',       'async function submitStatus'),
    ('Campanas historico',          'campaignLog'),
]

print(f"{'Funcionalidad':<35} {'test':^8} {'test2':^8}")
print("-" * 55)
for nombre, clave in features:
    t1 = 'OK' if clave in test1 else 'FALTA'
    t2 = 'OK' if clave in test2 else 'FALTA'
    print(f"{nombre:<35} {t1:^8} {t2:^8}")