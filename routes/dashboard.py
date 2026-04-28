"""Rutas Flask: Dashboard KPIs"""
from flask import Blueprint, jsonify
from database import get_db

dashboard_bp = Blueprint('dashboard', __name__)

@dashboard_bp.route('/kpis', methods=['GET'])
def kpis():
    conn = get_db()

    total_leads  = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    total_sent   = conn.execute("SELECT COUNT(*) FROM messages WHERE status='sent'").fetchone()[0]
    total_opened = conn.execute("SELECT COUNT(*) FROM messages WHERE opened_at IS NOT NULL").fetchone()[0]

    by_status = conn.execute('''
        SELECT status, COUNT(*) as cnt FROM lead_status GROUP BY status
    ''').fetchall()
    by_status = {r['status']: r['cnt'] for r in by_status}

    # Leads pendientes (no_enviado)
    no_enviado = by_status.get('no_enviado', 0)

    weekly = conn.execute('''
        SELECT strftime('%W', sent_at) as week,
               strftime('%Y', sent_at) as year,
               COUNT(*) as sent
        FROM messages WHERE status='sent'
        GROUP BY week, year ORDER BY year DESC, week DESC LIMIT 8
    ''').fetchall()

    top_comunas = conn.execute('''
        SELECT comuna, COUNT(*) as total,
               COUNT(CASE WHEN ls.status='interesado' THEN 1 END) as interesados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE comuna IS NOT NULL AND comuna != ''
        GROUP BY comuna ORDER BY total DESC LIMIT 8
    ''').fetchall()

    top_rubros = conn.execute('''
        SELECT l.rubro, COUNT(*) as total,
               COUNT(CASE WHEN ls.status='interesado' THEN 1 END) as interesados,
               COUNT(CASE WHEN ls.status='cerrado' THEN 1 END) as cerrados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.rubro IS NOT NULL AND l.rubro != ''
        GROUP BY l.rubro ORDER BY total DESC
    ''').fetchall()

    # Stats por categoria
    categoria_stats = conn.execute('''
        SELECT l.categoria,
               COUNT(DISTINCT l.id) as total,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) as interesados,
               COUNT(DISTINCT CASE WHEN ls.status='cerrado' THEN l.id END) as cerrados,
               COUNT(DISTINCT CASE WHEN ls.status='no_enviado' THEN l.id END) as pendientes,
               COUNT(DISTINCT CASE WHEN ls.status='enviado' THEN l.id END) as enviados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.categoria IS NOT NULL AND l.categoria != ''
        GROUP BY l.categoria ORDER BY total DESC
    ''').fetchall()

    optout_motivos = conn.execute(
        "SELECT optout_motivo as motivo, COUNT(*) as total FROM lead_status "
        "WHERE optout_motivo IS NOT NULL AND optout_motivo != '' "
        "GROUP BY optout_motivo ORDER BY total DESC"
    ).fetchall()

    opt_out  = conn.execute('SELECT COUNT(*) FROM opt_out').fetchone()[0]
    sellers  = conn.execute('SELECT COUNT(*) FROM sellers WHERE active=1').fetchone()[0]

    # ── Métricas prospects (Gestión > Interesados) ───────────────────
    try:
        prospects_total     = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
        prospects_cerrados  = conn.execute("SELECT COUNT(*) FROM prospects WHERE estado='cerrado'").fetchone()[0]
        prospects_no_logrado= conn.execute("SELECT COUNT(*) FROM prospects WHERE estado='no_logrado'").fetchone()[0]
        prospects_seguimiento = conn.execute(
            "SELECT COUNT(*) FROM prospects WHERE estado NOT IN ('cerrado','no_logrado')"
        ).fetchone()[0]
    except Exception:
        prospects_total = prospects_cerrados = prospects_no_logrado = prospects_seguimiento = 0

    # ── Métricas canal Email (et_contacts) ──────────────────────────
    try:
        email_enviados    = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE campaign_status IN ('enviado','seguimiento_48h','no_responde')"
        ).fetchone()[0]
        email_interesados = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE estado_interes IN ('interesado','quiere_reunion','en_negociacion','followup_wa_enviado')"
        ).fetchone()[0]
        email_respondidos = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE estado_interes IN ('respondido','interesado','quiere_reunion','en_negociacion','cerrado')"
        ).fetchone()[0]
        email_cerrados    = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE estado_interes='cerrado'"
        ).fetchone()[0]
        email_reuniones   = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE estado_interes='quiere_reunion'"
        ).fetchone()[0]
        email_no_responde = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE campaign_status='no_responde'"
        ).fetchone()[0]
        email_pendientes  = conn.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE campaign_status IN ('pendiente','no_enviado')"
        ).fetchone()[0]
        email_total       = conn.execute(
            "SELECT COUNT(*) FROM et_contacts"
        ).fetchone()[0]
        email_tasa_resp   = round(email_respondidos / email_enviados * 100, 1) if email_enviados else 0
    except Exception:
        email_enviados = email_interesados = email_respondidos = 0
        email_cerrados = email_reuniones = email_no_responde = 0
        email_pendientes = email_total = 0
        email_tasa_resp = 0

    conn.close()

    interesados = by_status.get('interesado', 0)
    reuniones   = by_status.get('quiere_reunion', 0)
    # Cerrados WA = lead_status cerrados + prospects cerrados (Gestión)
    cerrados    = by_status.get('cerrado', 0) + prospects_cerrados
    enviados    = by_status.get('enviado', 0)

    # Totales combinados (WA + Email)
    total_interesados = interesados + email_interesados
    total_cerrados    = cerrados    + email_cerrados
    total_reuniones   = reuniones   + email_reuniones

    tasa_apertura = round(total_opened / total_sent * 100, 1) if total_sent else 0
    tasa_interes  = round(total_interesados / (enviados + email_enviados) * 100, 1) if (enviados + email_enviados) else 0
    tasa_cierre   = round(total_cerrados / total_interesados * 100, 1) if total_interesados else 0

    return jsonify({
        'total_leads':    total_leads,
        'total_sent':     total_sent,
        'total_opened':   total_opened,
        'no_enviado':     no_enviado,
        'tasa_apertura':  tasa_apertura,
        'tasa_interes':   tasa_interes,
        'tasa_cierre':    tasa_cierre,
        'by_status':      by_status,
        # WA leads
        'wa_interesados': interesados + reuniones,  # interesado + quiere_reunion
        'wa_reuniones':   reuniones,
        'wa_cerrados':    cerrados,
        # Email leads
        'email_enviados':    email_enviados,
        'email_interesados': email_interesados,
        'email_respondidos': email_respondidos,
        'email_cerrados':    email_cerrados,
        'email_reuniones':   email_reuniones,
        'email_no_responde': email_no_responde,
        'email_pendientes':  email_pendientes,
        'email_total':       email_total,
        'email_tasa_resp':   email_tasa_resp,
        # Combinados
        'interesados':    total_interesados,
        'reuniones':      total_reuniones,
        'cerrados':       total_cerrados,
        'opt_out':        opt_out,
        'sellers_activos': sellers,
        'weekly_sends':   [dict(r) for r in weekly],
        'top_comunas':    [dict(r) for r in top_comunas],
        'top_rubros':     [dict(r) for r in top_rubros],
        'categoria_stats':[dict(r) for r in categoria_stats],
        'optout_motivos':[dict(r) for r in optout_motivos],
        # Gestión > Interesados desglose
        'prospects_total':       prospects_total,
        'prospects_cerrados':    prospects_cerrados,
        'prospects_seguimiento': prospects_seguimiento,
        'prospects_no_logrado':  prospects_no_logrado,
    })


@dashboard_bp.route('/preview', methods=['GET'])
def get_preview():
    from fidelizacion_config import ETAPAS
    conn = get_db()
    leads_pendientes = conn.execute("""
        SELECT l.name, l.rubro, l.comuna, ls.status
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE ls.status = 'no_enviado' AND l.phone IS NOT NULL
        ORDER BY ls.updated_at ASC LIMIT 40
    """).fetchall()

    rubros_count = {}
    for l in leads_pendientes:
        rk = dict(l).get('rubro','')
        rubros_count[rk] = rubros_count.get(rk,0) + 1
    top = sorted(rubros_count.items(), key=lambda x: x[1], reverse=True)[:3]
    rubros_str = ', '.join([f"{r}({n})" for r,n in top]) or 'Sin leads pendientes'

    sellers_etapas = []
    sellers = conn.execute("""
        SELECT s.name, s.phone, s.categoria,
            CAST(julianday('now','localtime') - julianday(s.closed_at) AS INTEGER) as dias
        FROM sellers s WHERE s.active=1 AND s.closed_at IS NOT NULL
    """).fetchall()
    for s in sellers:
        sd = dict(s)
        for d, key, nombre in ETAPAS:
            if sd.get('dias') == d:
                ya = conn.execute("SELECT COUNT(*) FROM messages WHERE phone=? AND message_type='fidelizacion' AND rubro=? AND status='sent'",
                    (sd['phone'], f'etapa_{d}')).fetchone()[0]
                if not ya:
                    sellers_etapas.append({'seller': sd['name'], 'etapa': nombre, 'dias': d})
    conn.close()

    return jsonify({
        'leads_pendientes': len(leads_pendientes),
        'rubros_preview': rubros_str,
        'fidelizacion_pendiente': len(sellers_etapas),
        'sellers_etapas': sellers_etapas[:5],
    })
