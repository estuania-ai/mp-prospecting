import sqlite3

# Mapa rubro key -> categoria (de rubros_config.py)
RUBRO_CATEGORIA = {
    'botilleria':     'Comercio de Alta Demanda Fin de Semana',
    'carniceria':     'Comercio de Alta Demanda Fin de Semana',
    'almacen':        'Comercio de Barrio Diario',
    'emporio':        'Comercio de Barrio Diario',
    'fruteria':       'Comercio de Barrio Diario',
    'minimarket':     'Comercio de Barrio Diario',
    'panaderia':      'Comercio de Barrio Diario',
    'verduleria':     'Comercio de Barrio Diario',
    'cafeteria':      'Gastronomia y Comida Rapida',
    'fuente_de_soda': 'Gastronomia y Comida Rapida',
    'pizzeria':       'Gastronomia y Comida Rapida',
    'sandwicheria':   'Gastronomia y Comida Rapida',
    'sushi':          'Gastronomia y Comida Rapida',
    'gimnasio':       'Membresias y Entrenamientos',
    'bazar':          'Retail Especializado y Hogar',
    'ferreteria':     'Retail Especializado y Hogar',
    'libreria':       'Retail Especializado y Hogar',
    'muebleria':      'Retail Especializado y Hogar',
    'farmacia':       'Salud y Farmacia',
    'spa':            'Servicios de Alto Ticket',
    'clinica_dental': 'Servicios de Alto Ticket',
    'taller':         'Servicios de Alto Ticket',
    'veterinaria':    'Servicios de Alto Ticket',
    'lavanderia':     'Servicios Personales Diario',
    'peluqueria':     'Servicios Personales Diario',
}

# Actualizar columna categoria en leads directamente en BD
conn = sqlite3.connect('data/prospecting.db')

# Verificar si existe columna categoria en leads
cols = [r[1] for r in conn.execute('PRAGMA table_info(leads)').fetchall()]
print('Columnas leads:', cols)

if 'categoria' not in cols:
    conn.execute('ALTER TABLE leads ADD COLUMN categoria TEXT')
    print('Columna categoria agregada')

# Actualizar categoria segun rubro
for rubro_key, categoria in RUBRO_CATEGORIA.items():
    conn.execute(
        'UPDATE leads SET categoria = ? WHERE rubro = ? AND (categoria IS NULL OR categoria = "")',
        (categoria, rubro_key)
    )

conn.commit()

# Verificar
stats = conn.execute("""
    SELECT rubro, categoria, COUNT(*) as total
    FROM leads
    GROUP BY rubro, categoria
    ORDER BY total DESC
""").fetchall()

print('\nRubro -> Categoria:')
for r in stats:
    print(f'  {r[0]} -> {r[1]} ({r[2]} leads)')

total_con = conn.execute("SELECT COUNT(*) FROM leads WHERE categoria IS NOT NULL AND categoria != ''").fetchone()[0]
total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
print(f'\nTotal: {total_con}/{total} leads con categoria')
conn.close()
print('OK')