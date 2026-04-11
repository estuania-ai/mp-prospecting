import os

files = {
    'ESTABLE_v5': r'C:\Users\juanspinto\Downloads\mp_dashboard_ESTABLE_v5.html',
    'ESTABLE_v6': r'C:\Users\juanspinto\Downloads\mp_dashboard_ESTABLE_v6.html',
    'test4': r'templates\dashboard_test4.html',
    'test5': r'templates\dashboard_test5.html',
}

features = [
    ('Modal cerrado con contacto',   'cerradoContacto'),
    ('Modal optout con motivos',     'optoutMotivo'),
    ('Boton seguimiento 🔔',         'sendSeguimiento'),
    ('Columna seguimiento 🟡🟡',     'seguimiento_72h'),
    ('Inteligencia nav',             'page-intel'),
    ('Scheduler batch_0930',         'batch_0930'),
    ('Rubros prospectados',          'rubrosTable'),
    ('Categorias stats',             'categoriasStats'),
    ('Badge no_enviado',             'badge-no_enviado'),
    ('Columna Categoria leads',      'l.categoria'),
    ('Toast HTML',                   'id="toast"'),
    ('onStatusChange',               'function onStatusChange'),
    ('submitStatus completo',        'async function submitStatus'),
    ('Estados barras resumen',       'statusBarsResumen'),
    ('Analisis rechazos',            'rechazosStats'),
    ('Export con motivo optout',     'Motivo Opt-out'),
    ('Export fecha seguimiento',     'Fecha Seg'),
    ('Mensaje Tiene MP',             'Tiene MP'),
    ('Campanas historico',           'campaignLog'),
]

contents = {}
for name, path in files.items():
    try:
        with open(path, 'r', encoding='utf-8') as f:
            contents[name] = f.read()
        print(f"{name}: {len(contents[name])} chars OK")
    except:
        contents[name] = ''
        print(f"{name}: NO ENCONTRADO")

print()
print(f"{'Funcionalidad':<35} {'v5':^6} {'v6':^6} {'test4':^6} {'test5':^6}")
print("-" * 60)
for nombre, clave in features:
    cols = []
    for name in ['ESTABLE_v5','ESTABLE_v6','test4','test5']:
        cols.append('OK' if clave in contents[name] else 'NO')
    print(f"{nombre:<35} {cols[0]:^6} {cols[1]:^6} {cols[2]:^6} {cols[3]:^6}")