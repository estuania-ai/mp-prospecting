"""Rutas Flask: Dashboard KPIs — con soporte de filtro mensual"""
from flask import Blueprint, jsonify, request
from flask_login import current_user, login_required
from database import get_db

dashboard_bp = Blueprint('dashboard', __name__)


def _date_clause(col, from_date, to_date, prefix='AND'):
    """Devuelve fragmento SQL para filtrar por rango de fechas."""
    if from_date and to_date:
        return f"{prefix} date({col}) BETWEEN '{from_date}' AND '{to_date}'"
    if from_date:
        return f"{prefix} date({col}) >= '{from_date}'"
    if to_date:
        return f"{prefix} date({col}) <= '{to_date}'"
    return ''


def _user_lead_ids(user, conn):
    """
    Devuelve lista de IDs de leads visibles al usuario.
    Owner: todos los leads (devuelve None = sin filtro)
    TL: leads asignados a su equipo (él + sus Sales)
    Sales: leads asignados solo a él
    """
    if not user or not user.is_authenticated or user.status != 'active':
        return []
    if user.role == 'owner':
        return None  # sin filtro
    if user.role == 'tl':
        rows = conn.execute(
            "SELECT id FROM leads WHERE assigned_to = ? OR assigned_to IN "
            "(SELECT id FROM users WHERE team_lead_id = ? AND status='active')",
            (user.id, user.id)
        ).fetchall()
        return [r['id'] for r in rows] or [-1]  # -1 si no tiene leads (para evitar IN ())
    if user.role == 'sales':
        rows = conn.execute(
            "SELECT id FROM leads WHERE assigned_to = ?", (user.id,)
        ).fetchall()
        return [r['id'] for r in rows] or [-1]
    return [-1]


def _scope_clause(lead_ids, col='lead_id'):
    """Construye AND lead_id IN (...) o '' si no aplica."""
    if lead_ids is None:
        return '', []
    if not lead_ids:
        return f' AND {col} IN (-1)', []
    placeholders = ','.join('?' * len(lead_ids))
    return f' AND {col} IN ({placeholders})', list(lead_ids)


@dashboard_bp.route('/kpis', methods=['GET'])
@login_required
def kpis():
    from_date = request.args.get('from', '').strip()
    to_date   = request.args.get('to', '').strip()

    df_msg      = _date_clause('sent_at',    from_date, to_date)
    df_ls       = _date_clause('updated_at', from_date, to_date)
    df_pro      = _date_clause('updated_at', from_date, to_date)
    # Para cerrados usamos la fecha real de cierre (closed_at).
    # Si una fila vieja no tiene closed_at, COALESCE cae a updated_at.
    df_pro_closed = _date_clause('COALESCE(closed_at, updated_at)', from_date, to_date)
    df_email    = _date_clause('fecha_envio', from_date, to_date)

    conn = get_db()

    # ── Filtro por rol: lista de leads visibles al usuario actual ──
    user_lead_ids = _user_lead_ids(current_user, conn)
    scope_msg, scope_msg_params = _scope_clause(user_lead_ids, 'lead_id')
    scope_ls,  scope_ls_params  = _scope_clause(user_lead_ids, 'lead_id')

    # Totales leads (pool acumulado — sin filtro de fecha)
    if user_lead_ids is None:
        total_leads = conn.execute('SELECT COUNT(*) FROM leads').fetchone()[0]
    else:
        total_leads = len(user_lead_ids) if -1 not in user_lead_ids else 0

    # ── Enviados: SOLO prospección, EXCLUYENDO números fijos (562XXXXXXX)
    total_sent   = conn.execute(
        f"SELECT COUNT(DISTINCT lead_id) FROM messages WHERE message_type='prospecting' AND status='sent' "
        f"AND NOT (phone LIKE '562%' OR phone LIKE '+562%') {df_msg} {scope_msg}",
        scope_msg_params
    ).fetchone()[0]
    total_opened = conn.execute(
        f"SELECT COUNT(DISTINCT lead_id) FROM messages WHERE message_type='prospecting' AND opened_at IS NOT NULL "
        f"AND NOT (phone LIKE '562%' OR phone LIKE '+562%') {df_msg} {scope_msg}",
        scope_msg_params
    ).fetchone()[0]

    # Estados lead_status en el periodo
    by_status = conn.execute(f'''
        SELECT status, COUNT(*) as cnt FROM lead_status
        WHERE 1=1 {df_ls} {scope_ls}
        GROUP BY status
    ''', scope_ls_params).fetchall()
    by_status = {r['status']: r['cnt'] for r in by_status}

    # Pendientes (no_enviado) — siempre estado actual, sin filtro fecha
    no_enviado = conn.execute(
        f"SELECT COUNT(*) FROM lead_status WHERE status='no_enviado' {scope_ls}",
        scope_ls_params
    ).fetchone()[0]

    # Filtro de prospects por rol
    if user_lead_ids is None:
        prospects_where_extra, prospects_extra_params = '', []
    elif user_lead_ids:
        prospects_where_extra = f' AND lead_id IN ({",".join("?"*len(user_lead_ids))})'
        prospects_extra_params = list(user_lead_ids)
    else:
        prospects_where_extra, prospects_extra_params = ' AND 1=0', []

    # ── Enviados por semana: SOLO prospección, EXCLUYENDO números fijos (562)
    weekly_raw = conn.execute(f'''
        SELECT strftime('%W', sent_at) as week,
               strftime('%Y', sent_at) as year,
               COUNT(DISTINCT lead_id) as sent
        FROM messages
        WHERE message_type='prospecting' AND status='sent'
          AND NOT (phone LIKE '562%' OR phone LIKE '+562%')
          {df_msg} {scope_msg}
        GROUP BY week, year ORDER BY year DESC, week DESC LIMIT 8
    ''', scope_msg_params).fetchall()

    # Interesados por semana = Prospects creados en Gestión (fuente de verdad)
    _wk_inter = {(r['week'], r['year']): r['cnt'] for r in conn.execute(f'''
        SELECT strftime('%W', created_at) as week, strftime('%Y', created_at) as year,
               COUNT(*) as cnt
        FROM prospects
        WHERE 1=1 {_date_clause('created_at', from_date, to_date)} {prospects_where_extra}
        GROUP BY week, year
    ''', prospects_extra_params).fetchall()}

    # Cerrados por semana — agrupa por la fecha REAL de cierre (closed_at)
    _wk_cerr = {(r['week'], r['year']): r['cnt'] for r in conn.execute(f'''
        SELECT strftime('%W', COALESCE(closed_at, updated_at)) as week,
               strftime('%Y', COALESCE(closed_at, updated_at)) as year,
               COUNT(*) as cnt
        FROM prospects WHERE estado='cerrado' {df_pro_closed} {prospects_where_extra}
        GROUP BY week, year
    ''', prospects_extra_params).fetchall()}

    # Opt-out por semana
    _wk_opto = {(r['week'], r['year']): r['cnt'] for r in conn.execute(f'''
        SELECT strftime('%W', updated_at) as week, strftime('%Y', updated_at) as year,
               COUNT(*) as cnt
        FROM lead_status WHERE status='opt_out' {df_ls} {scope_ls}
        GROUP BY week, year
    ''', scope_ls_params).fetchall()}

    # Quiere reunión por semana
    _wk_reunion = {(r['week'], r['year']): r['cnt'] for r in conn.execute(f'''
        SELECT strftime('%W', updated_at) as week, strftime('%Y', updated_at) as year,
               COUNT(*) as cnt
        FROM lead_status WHERE status='quiere_reunion' {df_ls} {scope_ls}
        GROUP BY week, year
    ''', scope_ls_params).fetchall()}

    # No interesado por semana
    _wk_no_int = {(r['week'], r['year']): r['cnt'] for r in conn.execute(f'''
        SELECT strftime('%W', updated_at) as week, strftime('%Y', updated_at) as year,
               COUNT(*) as cnt
        FROM lead_status WHERE status='no_interesado' {df_ls} {scope_ls}
        GROUP BY week, year
    ''', scope_ls_params).fetchall()}

    # Combinar en lista final
    weekly = []
    for r in weekly_raw:
        w, y = r['week'], r['year']
        s  = r['sent']
        i  = _wk_inter.get((w, y), 0)
        c  = _wk_cerr.get((w, y), 0)
        o  = _wk_opto.get((w, y), 0)
        re = _wk_reunion.get((w, y), 0)
        ni = _wk_no_int.get((w, y), 0)
        # Respuestas = suma de todos los estados activos de esa semana
        respuestas = i + c + o + re + ni
        weekly.append({
            'week': w, 'year': y, 'sent': s,
            'interesados':    i,
            'cerrados':       c,
            'optout':         o,
            'quiere_reunion': re,
            'no_interesado':  ni,
            'respuestas':     respuestas,
            'tasa_respuesta':      round(respuestas / s * 100, 1) if s else 0,
            'tasa_ventas':         round(c / respuestas * 100, 1) if respuestas else 0,
            'tasa_cierre_final':   round(c / i * 100, 1) if i else 0,
        })

    top_comunas = conn.execute(f'''
        SELECT comuna, COUNT(*) as total,
               COUNT(CASE WHEN ls.status='interesado' THEN 1 END) as interesados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE comuna IS NOT NULL AND comuna != '' {_date_clause('ls.updated_at', from_date, to_date)}
        GROUP BY comuna ORDER BY total DESC LIMIT 8
    ''').fetchall()

    # Filtro WHERE para tabla leads l.id
    leads_scope, leads_scope_params = _scope_clause(user_lead_ids, 'l.id')

    top_rubros = conn.execute(f'''
        SELECT l.rubro, COUNT(*) as total,
               COUNT(CASE WHEN ls.status='interesado' THEN 1 END) as interesados,
               COUNT(CASE WHEN ls.status='cerrado' THEN 1 END) as cerrados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.rubro IS NOT NULL AND l.rubro != '' {_date_clause('ls.updated_at', from_date, to_date)} {leads_scope}
        GROUP BY l.rubro ORDER BY total DESC
    ''', leads_scope_params).fetchall()

    categoria_stats = conn.execute(f'''
        SELECT l.categoria,
               COUNT(DISTINCT l.id) as total,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) as interesados,
               COUNT(DISTINCT CASE WHEN ls.status='cerrado' THEN l.id END) as cerrados,
               COUNT(DISTINCT CASE WHEN ls.status='no_enviado' THEN l.id END) as pendientes,
               COUNT(DISTINCT CASE WHEN ls.status='enviado' THEN l.id END) as enviados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.categoria IS NOT NULL AND l.categoria != '' {_date_clause('ls.updated_at', from_date, to_date)} {leads_scope}
        GROUP BY l.categoria ORDER BY total DESC
    ''', leads_scope_params).fetchall()

    optout_motivos = conn.execute(
        f"SELECT optout_motivo as motivo, COUNT(*) as total FROM lead_status "
        f"WHERE optout_motivo IS NOT NULL AND optout_motivo != '' {scope_ls} "
        f"GROUP BY optout_motivo ORDER BY total DESC",
        scope_ls_params
    ).fetchall()

    # opt_out: tabla opt_out tiene phone, no lead_id directo
    if user_lead_ids is None:
        opt_out  = conn.execute('SELECT COUNT(*) FROM opt_out').fetchone()[0]
    elif user_lead_ids:
        ph = ','.join('?'*len(user_lead_ids))
        opt_out = conn.execute(
            f"SELECT COUNT(*) FROM opt_out WHERE phone IN (SELECT phone FROM leads WHERE id IN ({ph}))",
            list(user_lead_ids)
        ).fetchone()[0]
    else:
        opt_out = 0

    # Sellers: solo Owner y TLs ven su contador real (no es lead-scoped, son sellers ganados)
    if current_user.role == 'sales':
        sellers = 0  # Sales no ve sellers
    else:
        sellers = conn.execute('SELECT COUNT(*) FROM sellers WHERE active=1').fetchone()[0]

    # ── Métricas prospects (filtrado por lead_id en pool del usuario) ──
    if user_lead_ids is None:
        prospects_filter = ''
        prospects_params = []
    elif user_lead_ids:
        ph = ','.join('?'*len(user_lead_ids))
        prospects_filter = f' AND lead_id IN ({ph})'
        prospects_params = list(user_lead_ids)
    else:
        prospects_filter = ' AND 1=0'
        prospects_params = []

    try:
        prospects_total = conn.execute(
            f"SELECT COUNT(*) FROM prospects WHERE 1=1 {prospects_filter}",
            prospects_params
        ).fetchone()[0]
        prospects_cerrados = conn.execute(
            f"SELECT COUNT(*) FROM prospects WHERE estado='cerrado' {df_pro_closed} {prospects_filter}",
            prospects_params
        ).fetchone()[0]
        prospects_no_logrado = conn.execute(
            f"SELECT COUNT(*) FROM prospects WHERE estado='no_logrado' {df_pro} {prospects_filter}",
            prospects_params
        ).fetchone()[0]
        prospects_seguimiento = conn.execute(
            f"SELECT COUNT(*) FROM prospects WHERE estado NOT IN ('cerrado','no_logrado') {prospects_filter}",
            prospects_params
        ).fetchone()[0]
        prospects_interesados = conn.execute(
            f"SELECT COUNT(*) FROM prospects WHERE estado='en_seguimiento' {prospects_filter}",
            prospects_params
        ).fetchone()[0]
        prospects_reunion = conn.execute(
            f"SELECT COUNT(*) FROM prospects WHERE estado='reunion_agendada' {prospects_filter}",
            prospects_params
        ).fetchone()[0]
    except Exception:
        prospects_total = prospects_cerrados = prospects_no_logrado = prospects_seguimiento = 0
        prospects_interesados = prospects_reunion = 0

    # ── Métricas canal Email — solo Owner/TL ven (Sales: 0, email pendiente para fase 4) ──
    if current_user.role == 'sales':
        email_enviados = email_interesados = email_respondidos = 0
        email_cerrados = email_reuniones = email_no_responde = 0
        email_pendientes = email_total = 0
        email_tasa_resp = 0
    else:
        try:
            email_enviados    = conn.execute(
                f"SELECT COUNT(*) FROM et_contacts "
                f"WHERE campaign_status IN ('enviado','seguimiento_48h','no_responde') {df_email}"
            ).fetchone()[0]
            email_interesados = conn.execute(
                f"SELECT COUNT(*) FROM et_contacts "
                f"WHERE estado_interes IN ('interesado','quiere_reunion','en_negociacion','followup_wa_enviado') {df_email}"
            ).fetchone()[0]
            email_respondidos = conn.execute(
                f"SELECT COUNT(*) FROM et_contacts "
                f"WHERE estado_interes IN ('respondido','interesado','quiere_reunion','en_negociacion','cerrado') {df_email}"
            ).fetchone()[0]
            email_cerrados    = conn.execute(
                f"SELECT COUNT(*) FROM et_contacts WHERE estado_interes='cerrado' {df_email}"
            ).fetchone()[0]
            email_reuniones   = conn.execute(
                f"SELECT COUNT(*) FROM et_contacts WHERE estado_interes='quiere_reunion' {df_email}"
            ).fetchone()[0]
            email_no_responde = conn.execute(
                f"SELECT COUNT(*) FROM et_contacts WHERE campaign_status='no_responde' {df_email}"
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

    # ── Interesados y reuniones desde Gestión (prospects) ─────────────
    # Evita desincronización entre Gestión y Leads
    interesados = prospects_interesados  # prospects con estado='en_seguimiento'
    reuniones   = prospects_reunion      # prospects con estado='reunion_agendada'
    enviados    = by_status.get('enviado', 0)  # Enviados de lead_status (impulse WA)

    # ── Cerrados WA: Gestión es fuente de verdad (evita duplicados)
    # Prospects cerrados en el periodo + lead_status cerrados sin prospect asociado
    wa_cerrados_ls = by_status.get('cerrado', 0)
    # Sólo sumar lead_status cerrados que NO tienen prospect (para no duplicar)
    # prospects_cerrados ya representa a todos los cierres gestionados
    # Si lead_status cerrado existe SIN prospect → sumarlo adicionalmente
    # Resultado: prospects_cerrados + lead_status cerrados huérfanos
    cerrados = prospects_cerrados + max(0, wa_cerrados_ls - prospects_cerrados)

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
        'wa_interesados': interesados + reuniones,
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
        'weekly_sends':   weekly,
        'top_comunas':    [dict(r) for r in top_comunas],
        'top_rubros':     [dict(r) for r in top_rubros],
        'categoria_stats':[dict(r) for r in categoria_stats],
        'optout_motivos': [dict(r) for r in optout_motivos],
        # Gestión > Interesados desglose
        'prospects_total':       prospects_total,
        'prospects_cerrados':    prospects_cerrados,
        'prospects_seguimiento': prospects_seguimiento,
        'prospects_no_logrado':  prospects_no_logrado,
        # Periodo aplicado
        'filtro_desde': from_date or None,
        'filtro_hasta': to_date   or None,
    })


# ═══════════════════════════════════════════════════════════════
# DIAGNÓSTICO de asignación de leads (Owner-only)
# ═══════════════════════════════════════════════════════════════
@dashboard_bp.route('/leads-diagnostic', methods=['GET'])
@login_required
def leads_diagnostic():
    """Diagnóstico rápido: cuántos leads existen, sin asignar, por pool, etc."""
    if current_user.role != 'owner':
        return jsonify({'error': 'Solo Owner'}), 403
    conn = get_db()
    total = conn.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
    unassigned_total = conn.execute(
        "SELECT COUNT(*) FROM leads WHERE assigned_to IS NULL"
    ).fetchone()[0]
    by_pool = conn.execute("""
        SELECT COALESCE(lead_pool,'(null)') as pool,
               COUNT(*) as total,
               SUM(CASE WHEN assigned_to IS NULL THEN 1 ELSE 0 END) as unassigned
        FROM leads
        GROUP BY lead_pool
    """).fetchall()
    no_enviado_unassigned = conn.execute("""
        SELECT COUNT(*) FROM leads l
        LEFT JOIN lead_status ls ON ls.lead_id = l.id
        WHERE ls.status = 'no_enviado' AND l.assigned_to IS NULL
    """).fetchone()[0]
    conn.close()
    return jsonify({
        'total_leads': total,
        'unassigned_total': unassigned_total,
        'no_enviado_unassigned': no_enviado_unassigned,
        'by_pool': [dict(r) for r in by_pool],
    })


@dashboard_bp.route('/email-cooldown-diagnostic', methods=['GET'])
@login_required
def email_cooldown_diagnostic():
    """
    Diagnostico del cooldown del email lote (Owner-only).
    Cuenta cuantos contactos NO_ENVIADO podrian enviarse hoy con
    cooldowns de 7/15/30 dias.
    """
    if current_user.role != 'owner':
        return jsonify({'error': 'Solo Owner'}), 403
    conn = get_db()
    out = {}
    for days in (7, 15, 30):
        # Disponibles = no_enviado/pendiente cuyo dominio NO recibio email
        # en los ultimos N dias
        sql = (
            "SELECT COUNT(*) FROM et_contacts c "
            "WHERE c.campaign_status IN ('no_enviado','pendiente') "
            "  AND c.email IS NOT NULL AND c.email LIKE '%@%' "
            "  AND NOT EXISTS ("
            "    SELECT 1 FROM et_contacts c2 "
            "    WHERE LOWER(SUBSTR(c2.email, INSTR(c2.email,'@')+1)) = "
            "          LOWER(SUBSTR(c.email,  INSTR(c.email,'@')+1)) "
            "      AND c2.campaign_status NOT IN ('no_enviado','pendiente','opt_out') "
            "      AND c2.fecha_envio >= datetime('now', '-' || ? || ' days') "
            "  )"
        )
        n = conn.execute(sql, (days,)).fetchone()[0]
        out[f'available_cooldown_{days}d'] = n
    out['total_no_enviado'] = conn.execute(
        "SELECT COUNT(*) FROM et_contacts WHERE campaign_status IN ('no_enviado','pendiente')"
    ).fetchone()[0]
    out['unique_domains_pool'] = conn.execute(
        "SELECT COUNT(DISTINCT LOWER(SUBSTR(email, INSTR(email,'@')+1))) "
        "FROM et_contacts "
        "WHERE campaign_status IN ('no_enviado','pendiente') "
        "  AND email IS NOT NULL AND email LIKE '%@%'"
    ).fetchone()[0]
    out['domains_blocked_30d'] = conn.execute(
        "SELECT COUNT(DISTINCT LOWER(SUBSTR(email, INSTR(email,'@')+1))) "
        "FROM et_contacts "
        "WHERE campaign_status NOT IN ('no_enviado','pendiente','opt_out') "
        "  AND fecha_envio >= datetime('now','-30 days')"
    ).fetchone()[0]
    conn.close()
    return jsonify(out)


@dashboard_bp.route('/leads-claim-owner', methods=['POST'])
@login_required
def leads_claim_owner():
    """
    Asigna al Owner actual todos los leads sin asignar del pool 'owner_personal'
    (o todos los NULL si el pool no está set). Reactiva el comportamiento
    histórico: los jobs corren sobre los leads del Owner.
    Body opcional: { "include_null_pool": true }
    """
    if current_user.role != 'owner':
        return jsonify({'error': 'Solo Owner'}), 403
    data = request.get_json(silent=True) or {}
    include_null_pool = bool(data.get('include_null_pool', True))
    conn = get_db()
    if include_null_pool:
        cur = conn.execute("""
            UPDATE leads SET assigned_to = ?
            WHERE assigned_to IS NULL
              AND (lead_pool = 'owner_personal' OR lead_pool IS NULL)
        """, (current_user.id,))
    else:
        cur = conn.execute("""
            UPDATE leads SET assigned_to = ?
            WHERE assigned_to IS NULL AND lead_pool = 'owner_personal'
        """, (current_user.id,))
    affected = cur.rowcount
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'claimed': affected, 'owner_id': current_user.id})


# ═══════════════════════════════════════════════════════════════
# SCHEDULER CONFIG por usuario (Sales/TL/Owner ve la suya)
# ═══════════════════════════════════════════════════════════════
SCHEDULER_FIELDS = [
    'prospeccion_0930_active', 'prospeccion_1500_active', 'prospeccion_1730_active',
    'seguimiento_24h_active', 'seguimiento_72h_active', 'fidelizacion_active',
    'email_lote1_active', 'email_lote2_active', 'email_lote3_active',
    'email_followup_active',
]


@dashboard_bp.route('/scheduler/user-config', methods=['GET'])
@login_required
def get_user_scheduler():
    """Devuelve la configuración personal del scheduler del usuario actual."""
    conn = get_db()
    row = conn.execute(
        'SELECT * FROM user_scheduler_config WHERE user_id=?', (current_user.id,)
    ).fetchone()
    if not row:
        # Crear con defaults (todos OFF)
        conn.execute('INSERT INTO user_scheduler_config (user_id) VALUES (?)', (current_user.id,))
        conn.commit()
        row = conn.execute(
            'SELECT * FROM user_scheduler_config WHERE user_id=?', (current_user.id,)
        ).fetchone()
    conn.close()
    return jsonify(dict(row))


@dashboard_bp.route('/scheduler/user-config', methods=['POST'])
@login_required
def set_user_scheduler():
    """Permite al usuario activar/desactivar sus jobs."""
    data = request.get_json() or {}
    conn = get_db()
    # Asegurar que el row existe
    conn.execute(
        'INSERT OR IGNORE INTO user_scheduler_config (user_id) VALUES (?)', (current_user.id,)
    )
    # Actualizar solo los campos válidos
    set_pairs, params = [], []
    for f in SCHEDULER_FIELDS:
        if f in data:
            set_pairs.append(f"{f}=?")
            params.append(1 if data[f] else 0)
    if 'daily_limit' in data:
        try:
            limit = max(0, min(int(data['daily_limit']), 1000))
            set_pairs.append('daily_limit=?')
            params.append(limit)
        except Exception:
            pass
    if 'email_daily_limit' in data:
        try:
            elimit = max(0, min(int(data['email_daily_limit']), 500))
            set_pairs.append('email_daily_limit=?')
            params.append(elimit)
        except Exception:
            pass
    if set_pairs:
        params.append(current_user.id)
        conn.execute(
            f"UPDATE user_scheduler_config SET {', '.join(set_pairs)}, "
            f"updated_at=datetime('now','localtime') WHERE user_id=?",
            params
        )
        conn.commit()
    row = conn.execute(
        'SELECT * FROM user_scheduler_config WHERE user_id=?', (current_user.id,)
    ).fetchone()
    conn.close()
    return jsonify({'ok': True, 'config': dict(row)})


@dashboard_bp.route('/preview', methods=['GET'])
@login_required
def get_preview():
    from fidelizacion_config import ETAPAS
    conn = get_db()
    # Filtro por rol
    user_lead_ids = _user_lead_ids(current_user, conn)
    scope_q, scope_p = _scope_clause(user_lead_ids, 'l.id')
    leads_pendientes = conn.execute(f"""
        SELECT l.name, l.rubro, l.comuna, ls.status
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE ls.status = 'no_enviado' AND l.phone IS NOT NULL {scope_q}
        ORDER BY ls.updated_at ASC LIMIT 40
    """, scope_p).fetchall()

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


# ═══════════════════════════════════════════════════════════════
# MÉTRICAS POR SALES — Panel del TL
# ═══════════════════════════════════════════════════════════════

@dashboard_bp.route('/tl-overview', methods=['GET'])
def tl_overview():
    """
    Resumen avanzado para TL — métricas estadísticas para gestión.
    """
    if not current_user.is_authenticated or current_user.status != 'active':
        return jsonify({'error': 'No autorizado'}), 401
    if current_user.role not in ('tl', 'owner'):
        return jsonify({'error': 'Solo TL/Owner'}), 403

    conn = get_db()

    # Pool sales (lo que el Owner alimenta)
    pool_total = conn.execute(
        "SELECT COUNT(*) AS c FROM leads WHERE lead_pool='sales_pool' "
        "AND NOT (phone LIKE '562%' OR phone LIKE '+562%')"
    ).fetchone()['c']
    pool_assigned = conn.execute(
        "SELECT COUNT(*) AS c FROM leads WHERE lead_pool='sales_pool' AND assigned_to IS NOT NULL "
        "AND NOT (phone LIKE '562%' OR phone LIKE '+562%')"
    ).fetchone()['c']

    # Métricas globales del equipo (suma de todos)
    total_enviados = conn.execute(
        "SELECT COUNT(DISTINCT lead_id) AS c FROM messages WHERE message_type='prospecting' AND status='sent' "
        "AND NOT (phone LIKE '562%' OR phone LIKE '+562%')"
    ).fetchone()['c']
    total_interesados = conn.execute(
        "SELECT COUNT(*) AS c FROM lead_status WHERE status='interesado'"
    ).fetchone()['c']
    total_cerrados = conn.execute(
        "SELECT COUNT(*) AS c FROM lead_status WHERE status='cerrado'"
    ).fetchone()['c']
    total_optout = conn.execute(
        "SELECT COUNT(*) AS c FROM lead_status WHERE status IN ('opt_out','no_interesado')"
    ).fetchone()['c']
    total_reunion = conn.execute(
        "SELECT COUNT(*) AS c FROM lead_status WHERE status='quiere_reunion'"
    ).fetchone()['c']
    total_no_enviado = conn.execute(
        "SELECT COUNT(*) AS c FROM lead_status WHERE status='no_enviado'"
    ).fetchone()['c']
    sellers_total = conn.execute(
        "SELECT COUNT(*) AS c FROM sellers WHERE active=1"
    ).fetchone()['c']

    # Ranking de Sales por conversión
    sales_ranking = conn.execute("""
        SELECT u.id, u.name, u.role, u.email,
               COUNT(DISTINCT l.id) AS total,
               COUNT(DISTINCT CASE WHEN ls.status='enviado' THEN l.id END) AS enviados,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) AS interesados,
               COUNT(DISTINCT CASE WHEN ls.status='cerrado' THEN l.id END) AS cerrados,
               COUNT(DISTINCT CASE WHEN ls.status IN ('opt_out','no_interesado') THEN l.id END) AS optout
        FROM users u
        LEFT JOIN leads l ON l.assigned_to = u.id
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE u.status='active' AND u.role IN ('owner','tl','sales')
        GROUP BY u.id
        ORDER BY cerrados DESC, interesados DESC
    """).fetchall()

    # Actividad por día (últimos 14)
    actividad_dias = conn.execute("""
        SELECT date(sent_at) AS dia,
               COUNT(DISTINCT lead_id) AS enviados
        FROM messages
        WHERE message_type='prospecting' AND status='sent'
          AND sent_at >= date('now','localtime','-14 days')
        GROUP BY date(sent_at) ORDER BY dia
    """).fetchall()

    # Distribución por rubro (top 8 con más interesados)
    top_rubros = conn.execute("""
        SELECT l.rubro,
               COUNT(DISTINCT l.id) AS total,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) AS interesados,
               COUNT(DISTINCT CASE WHEN ls.status='cerrado' THEN l.id END) AS cerrados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.rubro IS NOT NULL AND l.lead_pool='sales_pool'
        GROUP BY l.rubro
        HAVING total > 0
        ORDER BY interesados DESC, total DESC
        LIMIT 8
    """).fetchall()

    # Tareas pendientes en el sistema
    tareas_pendientes = conn.execute(
        "SELECT COUNT(*) AS c FROM tasks WHERE completada=0"
    ).fetchone()['c']

    # Usuarios pending de aprobación
    pending_users = conn.execute(
        "SELECT COUNT(*) AS c FROM users WHERE status='pending'"
    ).fetchone()['c']

    conn.close()

    # Cálculos de tasas
    tasa_envio = round((total_enviados / pool_total * 100), 1) if pool_total else 0
    tasa_respuesta = round((total_interesados + total_cerrados + total_optout + total_reunion) / total_enviados * 100, 1) if total_enviados else 0
    tasa_conversion = round((total_cerrados / total_interesados * 100), 1) if total_interesados else 0
    tasa_asignacion = round((pool_assigned / pool_total * 100), 1) if pool_total else 0

    return jsonify({
        'pool': {
            'total': pool_total,
            'assigned': pool_assigned,
            'unassigned': pool_total - pool_assigned,
            'pct_assigned': tasa_asignacion,
        },
        'equipo': {
            'enviados': total_enviados,
            'interesados': total_interesados,
            'cerrados': total_cerrados,
            'optout': total_optout,
            'reunion': total_reunion,
            'no_enviado': total_no_enviado,
            'sellers': sellers_total,
            'tasa_envio': tasa_envio,
            'tasa_respuesta': tasa_respuesta,
            'tasa_conversion': tasa_conversion,
        },
        'ranking': [dict(r) for r in sales_ranking],
        'actividad_14d': [dict(r) for r in actividad_dias],
        'top_rubros': [dict(r) for r in top_rubros],
        'sistema': {
            'tareas_pendientes': tareas_pendientes,
            'usuarios_pending': pending_users,
        }
    })


@dashboard_bp.route('/team-metrics', methods=['GET'])
def team_metrics():
    """
    Métricas agregadas por Sales del equipo del TL/Owner que llama.
    Owner: ve TODOS los Sales y TODOS los TLs (con su equipo)
    TL:    solo sus Sales + agregado total de OTROS TLs (sin detalle)
    Sales: 403
    """
    from flask_login import current_user
    if not current_user.is_authenticated or current_user.status != 'active':
        return jsonify({'error': 'No autorizado'}), 401
    if current_user.role not in ('tl', 'owner'):
        return jsonify({'error': 'Solo TL/Owner'}), 403

    conn = get_db()

    # Determinar qué Sales son visibles en detalle
    # CAMBIO: Tanto Owner como TL ven TODOS los Sales del sistema
    # (TL Josema gestiona todos los Sales, incluso al Owner como Sales)
    users_rows = conn.execute("""
        SELECT id, name, email, role, team_lead_id
        FROM users
        WHERE status='active' AND role IN ('sales','tl','owner')
        ORDER BY role DESC, name
    """).fetchall()

    visible_user_ids = [u['id'] for u in users_rows]

    # Métricas por usuario visible
    detail_rows = []
    for u in users_rows:
        uid = u['id']
        # Leads asignados
        total = conn.execute(
            'SELECT COUNT(*) AS c FROM leads WHERE assigned_to=?', (uid,)
        ).fetchone()['c']
        # Por estado
        by_status = conn.execute("""
            SELECT ls.status, COUNT(*) AS c
            FROM leads l
            LEFT JOIN lead_status ls ON l.id = ls.lead_id
            WHERE l.assigned_to=?
            GROUP BY ls.status
        """, (uid,)).fetchall()
        st = {r['status'] or 'sin_estado': r['c'] for r in by_status}

        enviados = (st.get('enviado',0) + st.get('abierto',0)
                    + st.get('interesado',0) + st.get('quiere_reunion',0)
                    + st.get('cerrado',0) + st.get('no_interesado',0)
                    + st.get('opt_out',0))
        interesados = st.get('interesado',0)
        cerrados = st.get('cerrado',0)
        opt_out = st.get('opt_out',0) + st.get('no_interesado',0)
        sin_enviar = st.get('no_enviado',0) + st.get('sin_estado',0)
        conv = round((interesados / total * 100), 1) if total else 0.0

        detail_rows.append({
            'user_id': uid,
            'name': u['name'],
            'email': u['email'],
            'role': u['role'],
            'team_lead_id': u['team_lead_id'],
            'leads_total': total,
            'sin_enviar': sin_enviar,
            'enviados': enviados,
            'interesados': interesados,
            'cerrados': cerrados,
            'opt_out': opt_out,
            'conversion_pct': conv,
        })

    # CAMBIO: Eliminamos "Otros equipos" — Josema (TL) ahora gestiona TODOS,
    # no necesita ver resumen agregado de otros equipos.
    conn.close()

    return jsonify({
        'role': current_user.role,
        'team_detail': detail_rows,
        'other_teams_summary': [],
    })
