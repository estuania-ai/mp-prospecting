"""
Herramienta de inteligencia de prospeccion
Analiza leads enviados y sugiere que rubros/comunas buscar para alimentar la BD
"""
from flask import Blueprint, jsonify
from flask_login import current_user, login_required
from database import get_db
from rubros_config import RUBROS

intel_bp = Blueprint('intel', __name__)


def _scope_clause():
    """Filtro WHERE por rol - sobre tabla leads (l)."""
    if not current_user or not current_user.is_authenticated:
        return ' AND 1=0', []
    if current_user.role == 'owner':
        return '', []
    if current_user.role == 'tl':
        return (' AND (l.assigned_to = ? OR l.assigned_to IN '
                '(SELECT id FROM users WHERE team_lead_id = ? AND status="active"))',
                [current_user.id, current_user.id])
    if current_user.role == 'sales':
        return ' AND l.assigned_to = ?', [current_user.id]
    return ' AND 1=0', []


@intel_bp.route('/suggestions', methods=['GET'])
@login_required
def get_suggestions():
    """
    Analiza el estado actual de leads y sugiere:
    1. Rubros con pocos leads (necesitan scraping)
    2. Comunas sin cobertura
    3. Categorias mas exitosas (mayor tasa de interes)
    4. Proximas busquedas recomendadas
    """
    conn = get_db()
    where_role, params_role = _scope_clause()

    # Leads por rubro con tasas (filtrados por rol)
    rubro_stats = conn.execute(f'''
        SELECT
            l.rubro,
            COUNT(DISTINCT l.id) as total_leads,
            COUNT(DISTINCT CASE WHEN ls.status = 'enviado' THEN l.id END) as enviados,
            COUNT(DISTINCT CASE WHEN ls.status = 'interesado' THEN l.id END) as interesados,
            COUNT(DISTINCT CASE WHEN ls.status = 'cerrado' THEN l.id END) as cerrados,
            COUNT(DISTINCT CASE WHEN ls.status = 'telefono_no_existe' THEN l.id END) as sin_telefono,
            COUNT(DISTINCT CASE WHEN ls.status IS NULL THEN l.id END) as pendientes
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE 1=1 {where_role}
        GROUP BY l.rubro
        ORDER BY total_leads DESC
    ''', params_role).fetchall()

    # Comunas por cobertura con tasa de respuesta
    comuna_stats = conn.execute('''
        SELECT
            l.comuna,
            COUNT(DISTINCT l.id) as total_leads,
            COUNT(DISTINCT l.rubro) as rubros_cubiertos,
            COUNT(DISTINCT CASE WHEN ls.status = 'interesado' THEN l.id END) as interesados,
            COUNT(DISTINCT CASE WHEN ls.status = 'cerrado' THEN l.id END) as cerrados,
            COUNT(DISTINCT CASE WHEN ls.status = 'no_interesado' THEN l.id END) as no_interesados,
            COUNT(DISTINCT CASE WHEN ls.status = 'enviado' THEN l.id END) as enviados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.comuna IS NOT NULL AND l.comuna != '' {where_role}
        GROUP BY l.comuna
        ORDER BY interesados DESC, total_leads DESC
    ''', params_role).fetchall()

    # Rubros con mejor tasa de interes
    best_rubros = conn.execute(f'''
        SELECT
            l.rubro,
            COUNT(DISTINCT l.id) as total,
            COUNT(DISTINCT CASE WHEN ls.status = 'interesado' THEN l.id END) as interesados,
            ROUND(COUNT(DISTINCT CASE WHEN ls.status = 'interesado' THEN l.id END) * 100.0 /
                NULLIF(COUNT(DISTINCT CASE WHEN ls.status IS NOT NULL THEN l.id END), 0), 1) as tasa_interes
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE 1=1 {where_role}
        GROUP BY l.rubro
        HAVING total > 3
        ORDER BY tasa_interes DESC
        LIMIT 5
    ''', params_role).fetchall()

    # Rubros sin leads (necesitan scraping urgente)
    rubros_con_leads = {r['rubro'] for r in rubro_stats}
    rubros_sin_leads = [
        {'key': k, 'label': v['label'], 'emoji': v['emoji'], 'categoria': v['categoria']}
        for k, v in RUBROS.items()
        if k not in rubros_con_leads
    ]

    # Generar sugerencias de busqueda
    suggestions = []

    # 1. Rubros sin leads - prioridad alta
    for r in rubros_sin_leads[:5]:
        suggestions.append({
            'prioridad': 'alta',
            'tipo': 'rubro_sin_leads',
            'rubro_key': r['key'],
            'rubro_label': r['label'],
            'emoji': r['emoji'],
            'categoria': r['categoria'],
            'mensaje': f"Sin leads para {r['label']} — buscar en Google Maps",
            'query_sugerida': f"{r['label']} en Santiago",
        })

    # 2. Rubros con pocos leads pendientes
    for r in rubro_stats:
        if r['pendientes'] < 5 and r['total_leads'] > 0:
            rubro_info = RUBROS.get(r['rubro'], {})
            suggestions.append({
                'prioridad': 'media',
                'tipo': 'pocos_pendientes',
                'rubro_key': r['rubro'],
                'rubro_label': rubro_info.get('label', r['rubro']),
                'emoji': rubro_info.get('emoji', ''),
                'categoria': rubro_info.get('categoria', ''),
                'mensaje': f"Solo {r['pendientes']} leads pendientes para {r['rubro']}",
                'query_sugerida': f"{rubro_info.get('label', r['rubro'])} en Santiago",
            })

    # 3. Comunas con alta tasa de interes pero pocos leads
    for c in comuna_stats:
        if c['interesados'] > 0 and c['total_leads'] < 20:
            suggestions.append({
                'prioridad': 'alta',
                'tipo': 'comuna_exitosa_sin_cobertura',
                'comuna': c['comuna'],
                'mensaje': f"{c['comuna']} tiene {c['interesados']} interesados pero solo {c['total_leads']} leads totales",
                'query_sugerida': f"negocios en {c['comuna']}",
            })

    conn.close()

    return jsonify({
        'rubro_stats': [dict(r) for r in rubro_stats],
        'comuna_stats': [dict(r) for r in comuna_stats],
        'best_rubros': [dict(r) for r in best_rubros],
        'rubros_sin_leads': rubros_sin_leads,
        'suggestions': suggestions[:10],
        'resumen': {
            'total_rubros_con_leads': len(rubro_stats),
            'total_rubros_sin_leads': len(rubros_sin_leads),
            'comunas_cubiertas': len(comuna_stats),
            'sugerencias_pendientes': len(suggestions),
        }
    })


@intel_bp.route('/next-searches', methods=['GET'])
def next_searches():
    """Genera lista priorizada de proximas busquedas Google Maps"""
    conn = get_db()

    # Comunas con mas interesados (expandir ahi)
    top_comunas = conn.execute('''
        SELECT l.comuna,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) as interesados,
               COUNT(DISTINCT l.rubro) as rubros_actuales
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        GROUP BY l.comuna
        ORDER BY interesados DESC
        LIMIT 10
    ''').fetchall()

    # Rubros con mejor conversion
    top_rubros = conn.execute('''
        SELECT l.rubro,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) as interesados,
               COUNT(DISTINCT l.id) as total
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        GROUP BY l.rubro
        HAVING interesados > 0
        ORDER BY interesados DESC
        LIMIT 5
    ''').fetchall()

    conn.close()

    # Cruzar: mejores rubros X mejores comunas
    searches = []
    for rubro in top_rubros:
        rubro_info = RUBROS.get(rubro['rubro'], {})
        for comuna in top_comunas[:5]:
            searches.append({
                'query': f"{rubro_info.get('label', rubro['rubro'])} en {comuna['comuna']}",
                'rubro_key': rubro['rubro'],
                'rubro_label': rubro_info.get('label', rubro['rubro']),
                'emoji': rubro_info.get('emoji', ''),
                'comuna': comuna['comuna'],
                'razon': f"Rubro con {rubro['interesados']} interesados + comuna con {comuna['interesados']} interesados",
                'maps_url_base': f"https://www.google.com/maps/search/{rubro_info.get('label', rubro['rubro'])}+en+{comuna['comuna']}"
            })

    return jsonify({
        'next_searches': searches[:15],
        'top_comunas': [dict(r) for r in top_comunas],
        'top_rubros': [dict(r) for r in top_rubros],
    })
