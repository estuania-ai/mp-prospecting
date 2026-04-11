"""Rutas Flask: Scraping via Apify"""
from flask import Blueprint, request, jsonify
from database import get_config, set_config
from apify_scraper import ApifyScraper, COMUNAS_RM, RUBRO_QUERIES
import threading

scraping_bp = Blueprint('scraping', __name__)


def _run_url_async(maps_url: str, rubro: str, comuna: str):
    from database import get_db
    token = get_config('apify_token')
    if not token:
        return

    # Registrar inicio en historial
    conn = get_db()
    cur = conn.execute(
        "INSERT INTO scraping_jobs (tipo, rubro, comuna, maps_url, status) VALUES (?, ?, ?, ?, 'running')",
        ('url', rubro or '', comuna or '', maps_url)
    )
    job_id = cur.lastrowid
    conn.commit()
    conn.close()

    try:
        scraper = ApifyScraper(token)
        result = scraper.scrape_from_url(maps_url, rubro or None, comuna or None, max_items=100)

        conn2 = get_db()
        conn2.execute(
            "UPDATE scraping_jobs SET status='succeeded', leads_found=?, leads_inserted=?, leads_skipped=?, finished_at=datetime('now','localtime') WHERE id=?",
            (result.get('leads_found', 0), result.get('inserted', 0), result.get('skipped', 0), job_id)
        )
        conn2.commit()
        conn2.close()

        import logging
        logging.getLogger(__name__).info(f"Scraping URL terminado: {result}")

    except Exception as e:
        conn3 = get_db()
        conn3.execute(
            "UPDATE scraping_jobs SET status='failed', error=?, finished_at=datetime('now','localtime') WHERE id=?",
            (str(e), job_id)
        )
        conn3.commit()
        conn3.close()


def _run_search_async(rubro_key: str, comuna: str, max_items: int):
    token = get_config('apify_token')
    if not token:
        return
    scraper = ApifyScraper(token)
    result  = scraper.scrape_and_save(rubro_key, comuna, max_items)
    import logging
    logging.getLogger(__name__).info(f"Scraping texto terminado: {result}")


@scraping_bp.route('/run', methods=['POST'])
def run_scraping():
    d        = request.json
    maps_url = d.get('maps_url', '').strip()
    rubro    = d.get('rubro', '').strip()
    comuna   = d.get('comuna', '').strip()

    token = get_config('apify_token')
    if not token:
        return jsonify({'error': 'Apify token no configurado. Ve a Configuracion.'}), 400

    # MODO 1: URL directa de Google Maps
    if maps_url:
        t = threading.Thread(target=_run_url_async, args=(maps_url, rubro, comuna))
        t.daemon = True
        t.start()
        return jsonify({'ok': True, 'message': f'Scraping iniciado con URL de Google Maps', 'modo': 'url'})

    # MODO 2: rubro + comuna
    if rubro and comuna:
        max_items = int(d.get('max_items', 40))
        t = threading.Thread(target=_run_search_async, args=(rubro, comuna, max_items))
        t.daemon = True
        t.start()
        return jsonify({'ok': True, 'message': f'Scraping iniciado: {rubro} en {comuna}', 'modo': 'search'})

    return jsonify({'error': 'Ingresa una URL de Google Maps o selecciona rubro + comuna'}), 400


@scraping_bp.route('/comunas', methods=['GET'])
def get_comunas():
    return jsonify(COMUNAS_RM)


@scraping_bp.route('/rubros', methods=['GET'])
def get_rubros():
    from rubros_config import RUBROS
    return jsonify([
        {'key': k, 'label': v['label'], 'emoji': v['emoji']}
        for k, v in RUBROS.items()
    ])


@scraping_bp.route('/config', methods=['POST'])
def save_config():
    d = request.json
    for key, value in d.items():
        set_config(key, value)
    return jsonify({'ok': True})


@scraping_bp.route('/config', methods=['GET'])
def load_config():
    keys = ['apify_token', 'exec_name', 'exec_phone',
            'calendar_link', 'daily_limit', 'min_delay_sec', 'max_delay_sec']
    from database import get_config as gc
    return jsonify({k: gc(k) for k in keys})


@scraping_bp.route('/history', methods=['GET'])
def get_history():
    from database import get_db
    conn = get_db()
    rows = conn.execute("""
        SELECT id, run_id, tipo, rubro, comuna, maps_url, status,
               leads_found, leads_inserted, leads_skipped, error,
               started_at, finished_at
        FROM scraping_jobs ORDER BY started_at DESC LIMIT 20
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@scraping_bp.route('/metrics', methods=['GET'])
def get_metrics():
    from database import get_db
    conn = get_db()
    
    # Leads por rubro
    por_rubro = conn.execute("""
        SELECT l.rubro, COUNT(*) as total,
               COUNT(CASE WHEN ls.status != 'no_enviado' THEN 1 END) as enviados,
               COUNT(CASE WHEN ls.status = 'interesado' THEN 1 END) as interesados
        FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.rubro IS NOT NULL AND l.rubro != ''
        GROUP BY l.rubro ORDER BY total DESC
    """).fetchall()

    # Cobertura por comuna
    por_comuna = conn.execute("""
        SELECT l.comuna, COUNT(*) as total,
               COUNT(CASE WHEN ls.status != 'no_enviado' THEN 1 END) as enviados,
               COUNT(CASE WHEN ls.status = 'interesado' THEN 1 END) as interesados
        FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.comuna IS NOT NULL AND l.comuna != ''
        GROUP BY l.comuna ORDER BY total DESC
    """).fetchall()

    # Stats generales
    total = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    conn.close()

    return jsonify({
        'total_leads': total,
        'por_rubro': [dict(r) for r in por_rubro],
        'por_comuna': [dict(r) for r in por_comuna]
    })


@scraping_bp.route('/validate-token', methods=['POST'])
def validate_token():
    """Valida token Apify, verifica actor y alerta si hay problemas"""
    import requests as req
    token = get_config('apify_token')
    if not token:
        return jsonify({'ok': False, 'error': 'Token no configurado'})
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # 1. Validar token
        r = req.get('https://api.apify.com/v2/users/me', headers=headers, timeout=5)
        if r.status_code != 200:
            return jsonify({'ok': False, 'error': f'Token invalido (HTTP {r.status_code}). Verifica que el token sea correcto.'})
        
        user = r.json().get('data', {}).get('username', '')
        
        # 2. Verificar actor configurado - intentar por ID y por nombre
        actor_id = get_config('apify_actor_id') or 'compass/google-maps-extractor'
        r2 = req.get(f'https://api.apify.com/v2/acts/{actor_id}', headers=headers, timeout=5)
        # Si falla por nombre, intentar buscar en runs recientes
        if r2.status_code != 200:
            r_runs = req.get('https://api.apify.com/v2/actor-runs?limit=5', headers=headers, timeout=5)
            if r_runs.status_code == 200:
                runs = r_runs.json().get('data', {}).get('items', [])
                if runs:
                    actor_id_from_runs = runs[0].get('actId', '')
                    if actor_id_from_runs:
                        r2b = req.get(f'https://api.apify.com/v2/acts/{actor_id_from_runs}', headers=headers, timeout=5)
                        if r2b.status_code == 200:
                            r2 = r2b
                            actor_id = actor_id_from_runs
                            set_config('apify_actor_id', actor_id)
        
        actor_ok = r2.status_code == 200
        actor_nombre = r2.json().get('data', {}).get('name', actor_id) if actor_ok else None

        # 3. Si actor no existe, buscar alternativas
        actores_disponibles = []
        if not actor_ok:
            r3 = req.get('https://api.apify.com/v2/acts?limit=20', headers=headers, timeout=5)
            if r3.status_code == 200:
                acts = r3.json().get('data', {}).get('items', [])
                actores_disponibles = [
                    {'id': a.get('id'), 'name': a.get('name'), 'full': a.get('username','') + '/' + a.get('name','')}
                    for a in acts
                    if 'maps' in (a.get('name','') or '').lower() or 'google' in (a.get('name','') or '').lower()
                ]

        return jsonify({
            'ok': True,
            'user': user,
            'actor_id': actor_id,
            'actor_ok': actor_ok,
            'actor_nombre': actor_nombre,
            'actores_disponibles': actores_disponibles,
            'alerta': None if actor_ok else f'El actor "{actor_id}" no existe en esta cuenta. Selecciona uno disponible.'
        })
        
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@scraping_bp.route('/set-actor', methods=['POST'])
def set_actor():
    """Cambia el actor ID configurado"""
    actor_id = (request.json or {}).get('actor_id', '')
    if not actor_id:
        return jsonify({'error': 'actor_id requerido'}), 400
    set_config('apify_actor_id', actor_id)
    return jsonify({'ok': True})


@scraping_bp.route('/detect-actor', methods=['POST'])
def detect_actor():
    """Detecta el actor de Google Maps desde el historial de runs de Apify"""
    import requests as req
    token = get_config('apify_token')
    if not token:
        return jsonify({'error': 'Token no configurado'})
    
    headers = {'Authorization': f'Bearer {token}'}
    
    try:
        # Buscar en runs recientes para detectar el actor usado
        r = req.get('https://api.apify.com/v2/actor-runs?limit=10', headers=headers, timeout=5)
        if r.status_code == 200:
            runs = r.json().get('data', {}).get('items', [])
            if runs:
                # Tomar el actor del run mas reciente
                actor_id = runs[0].get('actId', '')
                if actor_id:
                    # Guardar automaticamente
                    set_config('apify_actor_id', actor_id)
                    return jsonify({'ok': True, 'actor_id': actor_id})
        
        return jsonify({'ok': False, 'error': 'No se encontraron runs previos'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)})


@scraping_bp.route('/apify-runs', methods=['GET'])
def get_apify_runs():
    """Obtiene lista de runs recientes desde Apify"""
    import requests as req
    token = get_config('apify_token')
    if not token:
        return jsonify({'error': 'Token no configurado'})
    
    headers = {'Authorization': f'Bearer {token}'}
    try:
        r = req.get('https://api.apify.com/v2/actor-runs?limit=10&desc=1', headers=headers, timeout=10)
        if r.status_code != 200:
            return jsonify({'error': f'Error Apify: {r.status_code}'})
        
        runs = r.json().get('data', {}).get('items', [])
        result = []
        for run in runs:
            run_id = run.get('id')
            dataset_id = run.get('defaultDatasetId', '')
            item_count = 0
            # Obtener cantidad real de items del dataset
            if dataset_id:
                try:
                    rd = req.get(f'https://api.apify.com/v2/datasets/{dataset_id}', headers=headers, timeout=5)
                    if rd.status_code == 200:
                        item_count = rd.json().get('data', {}).get('itemCount', 0)
                except:
                    pass
            result.append({
                'id': run_id,
                'status': run.get('status'),
                'startedAt': run.get('startedAt',''),
                'itemCount': item_count
            })
        return jsonify({'runs': result})
    except Exception as e:
        return jsonify({'error': str(e)})


@scraping_bp.route('/cargar-leads', methods=['POST'])
def cargar_leads_manual():
    """Carga leads desde un run especifico de Apify"""
    import requests as req
    import re
    from database import get_db
    
    data = request.json or {}
    run_id = data.get('run_id', '')
    rubro = data.get('rubro', '')
    categoria = data.get('categoria', '')
    descripcion = data.get('descripcion', 'Carga manual')
    
    if not run_id or not rubro:
        return jsonify({'error': 'run_id y rubro son requeridos'}), 400
    
    token = get_config('apify_token')
    if not token:
        return jsonify({'error': 'Token Apify no configurado'}), 400
    
    headers = {'Authorization': f'Bearer {token}'}
    
    COMUNAS = ['Cerrillos','Cerro Navia','Conchalí','El Bosque','Estación Central',
        'Huechuraba','Independencia','La Cisterna','La Florida','La Granja',
        'La Pintana','La Reina','Las Condes','Lo Barnechea','Lo Espejo',
        'Lo Prado','Macul','Maipú','Ñuñoa','Peñalolén','Providencia',
        'Pudahuel','Puente Alto','Quilicura','Quinta Normal','Recoleta',
        'Renca','San Bernardo','San Joaquín','San Miguel','San Ramón',
        'Santiago','Vitacura','Buin','Colina','El Monte','Lampa',
        'Melipilla','Paine','Pirque','Tiltil']

    def extraer_comuna(address):
        if not address: return ''
        addr_lower = address.lower()
        for c in COMUNAS:
            if c.lower() in addr_lower:
                return c
        return ''

    try:
        r = req.get(
            f'https://api.apify.com/v2/actor-runs/{run_id}/dataset/items?limit=200',
            headers=headers, timeout=30
        )
        if r.status_code != 200:
            return jsonify({'error': f'Error descargando dataset: {r.status_code}'}), 400
        
        items = r.json()
        conn = get_db()
        insertados = 0
        duplicados = 0
        sin_telefono = 0

        for item in items:
            name = (item.get('title') or '').strip()
            phone_raw = (item.get('phone') or '').strip()
            phone_raw = re.sub(r'\D', '', phone_raw)
            addr = item.get('address', '') or ''

            if not name or not phone_raw:
                sin_telefono += 1
                continue

            # Validar formato: solo 569XXXXXXXX
            if re.match(r'^9\d{8}$', phone_raw):
                phone = '56' + phone_raw
            elif re.match(r'^569\d{8}$', phone_raw):
                phone = phone_raw
            else:
                sin_telefono += 1
                continue

            # Verificar duplicado
            existing = conn.execute('SELECT id FROM leads WHERE phone=?', (phone,)).fetchone()
            if existing:
                duplicados += 1
                continue

            comuna = extraer_comuna(addr)

            cur = conn.execute(
                'INSERT INTO leads (name, phone, comuna, rubro, categoria) VALUES (?, ?, ?, ?, ?)',
                (name, phone, comuna, rubro, categoria)
            )
            lead_id = cur.lastrowid
            conn.execute(
                "INSERT INTO lead_status (lead_id, status, updated_at) VALUES (?, 'no_enviado', datetime('now','localtime'))",
                (lead_id,)
            )
            insertados += 1

        # Registrar en historial
        conn.execute("""
            INSERT INTO scraping_jobs (run_id, tipo, rubro, maps_url, status, leads_found, leads_inserted, leads_skipped, finished_at)
            VALUES (?, 'manual', ?, ?, 'succeeded', ?, ?, ?, datetime('now','localtime'))
        """, (run_id, rubro, descripcion, len(items), insertados, duplicados + sin_telefono))

        conn.commit()
        conn.close()

        return jsonify({
            'ok': True,
            'insertados': insertados,
            'duplicados': duplicados,
            'sin_telefono': sin_telefono,
            'total': len(items)
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500
