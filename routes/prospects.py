"""
Rutas Flask: Prospectos Interesados + Agenda de Tareas
"""
from flask import Blueprint, request, jsonify
from database import get_db
from datetime import datetime

prospects_bp = Blueprint('prospects', __name__)

COMPETENCIA = ['Tbk', 'Sumup', 'Getnet', 'BCI', 'Banco Chile', 'Compra Aqui', 'TUU', 'Otra', 'Sin competencia']

MSG_INFO = "Hola! Claro que si, muchas gracias por el interes. Para resumirte lo mas importante de la imagen: Es que tienes beneficios para cualquier necesidad de tu negocio, ya sea liquidez, creditos, Cuotas sin interes, Boletas, etc lo que necesites segun tu negocio. Dime, Que necesitas hoy en dia?, te tinca si te pego una llamadita corta de 5 minutos, tu me dices cuando o bien agendamos un dia en la semana para vernos, lo que sea mas comodo para ti, revisamos de forma super transparente si realmente te conviene el cambio. La idea es asesorarte. Me avisas que tengas un gran dia."

MSG_SEGUIMIENTO = "Hola, como estas? Te escribo cortito porque de la ultima vez que conversamos no tuve respuesta y queria saber si te quedo alguna duda. Te parece si agendamos una llamada rapida o paso a visitarte al local para revisarlo sin compromiso? Quedo super atento a lo que te acomode!"

# ── PROSPECTS ─────────────────────────────────────────

@prospects_bp.route('/', methods=['GET'])
def get_prospects():
    conn = get_db()
    rows = conn.execute("""
        SELECT p.*, 
               COUNT(CASE WHEN t.completada=0 THEN 1 END) as tareas_pendientes,
               COUNT(t.id) as total_tareas
        FROM prospects p
        LEFT JOIN tasks t ON p.id = t.prospect_id
        GROUP BY p.id
        ORDER BY p.updated_at DESC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@prospects_bp.route('/', methods=['POST'])
def create_prospect():
    data = request.json
    conn = get_db()
    
    # Verificar si ya existe por lead_id
    if data.get('lead_id'):
        existing = conn.execute(
            'SELECT id FROM prospects WHERE lead_id = ?', (data['lead_id'],)
        ).fetchone()
        if existing:
            conn.close()
            return jsonify({'ok': True, 'id': existing['id'], 'existing': True})
    
    cur = conn.execute("""
        INSERT INTO prospects (lead_id, name, phone, negocio, rubro, categoria, comuna, competencia, procedencia, notas, direccion)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('lead_id'), data.get('name'), data.get('phone'),
        data.get('negocio'), data.get('rubro'), data.get('categoria'),
        data.get('comuna'), data.get('competencia', ''),
        data.get('procedencia', 'Online'), data.get('notas', ''),
        data.get('direccion', '')
    ))
    conn.commit()
    prospect_id = cur.lastrowid

    # ── Sincronizar lead_status si tiene lead_id ─────────────────────
    lead_id = data.get('lead_id')
    if lead_id:
        conn.execute("""
            INSERT INTO lead_status (lead_id, status, notes, updated_at)
            VALUES (?, 'interesado', 'Agregado a Gestión', datetime('now','localtime'))
            ON CONFLICT(lead_id) DO UPDATE SET
                status='interesado',
                notes='Actualizado desde Gestión',
                updated_at=datetime('now','localtime')
        """, (lead_id,))
        conn.commit()

    conn.close()
    return jsonify({'ok': True, 'id': prospect_id})


@prospects_bp.route('/<int:pid>', methods=['PUT'])
def update_prospect(pid):
    data = request.json
    conn = get_db()
    conn.execute("""
        UPDATE prospects SET
            name=?, phone=?, negocio=?, rubro=?, categoria=?, comuna=?,
            competencia=?, procedencia=?, notas=?, direccion=?,
            updated_at=datetime('now','localtime')
        WHERE id=?
    """, (
        data.get('name',''),
        data.get('phone',''),
        data.get('negocio',''),
        data.get('rubro',''),
        data.get('categoria',''),
        data.get('comuna',''),
        data.get('competencia',''),
        data.get('procedencia','Online'),
        data.get('notas',''),
        data.get('direccion',''),
        pid
    ))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@prospects_bp.route('/config', methods=['GET'])
def get_config():
    return jsonify({
        'competencia': COMPETENCIA,
        'msg_info': MSG_INFO,
        'msg_seguimiento': MSG_SEGUIMIENTO
    })


@prospects_bp.route('/<int:pid>/send', methods=['POST'])
def send_message(pid):
    data = request.json
    msg = data.get('message', '')
    conn = get_db()
    prospect = conn.execute('SELECT * FROM prospects WHERE id=?', (pid,)).fetchone()
    conn.close()
    if not prospect:
        return jsonify({'error': 'Prospecto no encontrado'}), 404
    prospect = dict(prospect)
    
    import threading
    def _send():
        try:
            from whatsapp.sender_desktop import get_sender
            from database import get_db as _db
            sender = get_sender()
            if not sender._is_logged_in:
                sender.start()
            result = sender.send_message(prospect['phone'], msg, None)
            c = _db()
            c.execute(
                "INSERT INTO messages (lead_id, phone, message_type, status, sent_at) VALUES (?,?,?,?,datetime('now','localtime'))",
                (prospect.get('lead_id'), prospect['phone'],
                 'prospecto_seguimiento', 'sent' if result['success'] else 'failed')
            )
            c.commit()
            c.close()
        except Exception as e:
            import logging
            logging.getLogger(__name__).error(f"Error send prospect: {e}")
    threading.Thread(target=_send, daemon=True).start()
    return jsonify({'ok': True})


# ── TASKS ─────────────────────────────────────────────

@prospects_bp.route('/<int:pid>/tasks', methods=['GET'])
def get_tasks(pid):
    conn = get_db()
    rows = conn.execute("""
        SELECT t.*, p.name, p.phone, p.negocio, p.rubro
        FROM tasks t
        JOIN prospects p ON t.prospect_id = p.id
        WHERE t.prospect_id = ?
        ORDER BY t.fecha ASC, t.hora ASC
    """, (pid,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@prospects_bp.route('/tasks/today', methods=['GET'])
def get_tasks_today():
    conn = get_db()
    rows = conn.execute("""
        SELECT t.*, p.name, p.phone, p.negocio, p.rubro, p.categoria
        FROM tasks t
        JOIN prospects p ON t.prospect_id = p.id
        WHERE date(t.fecha) <= date('now','localtime')
          AND t.completada = 0
        ORDER BY t.fecha ASC, t.hora ASC
    """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@prospects_bp.route('/tasks/calendar', methods=['GET'])
def get_tasks_calendar():
    week = request.args.get('week', '')
    conn = get_db()
    if week:
        rows = conn.execute("""
            SELECT t.*, p.name, p.phone, p.negocio, p.rubro
            FROM tasks t
            JOIN prospects p ON t.prospect_id = p.id
            WHERE strftime('%W-%Y', t.fecha) = ?
            ORDER BY t.fecha ASC, t.hora ASC
        """, (week,)).fetchall()
    else:
        rows = conn.execute("""
            SELECT t.*, p.name, p.phone, p.negocio, p.rubro
            FROM tasks t
            JOIN prospects p ON t.prospect_id = p.id
            WHERE t.fecha >= date('now','localtime','-1 day')
              AND t.fecha <= date('now','localtime','+14 day')
            ORDER BY t.fecha ASC, t.hora ASC
        """).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@prospects_bp.route('/<int:pid>/tasks', methods=['POST'])
def create_task(pid):
    data = request.json
    conn = get_db()
    prospect = conn.execute('SELECT lead_id FROM prospects WHERE id=?', (pid,)).fetchone()
    lead_id = prospect['lead_id'] if prospect else None
    cur = conn.execute("""
        INSERT INTO tasks (prospect_id, lead_id, tipo, descripcion, fecha, hora)
        VALUES (?, ?, ?, ?, ?, ?)
    """, (pid, lead_id, data.get('tipo','llamada'),
          data.get('descripcion',''), data.get('fecha'), data.get('hora','')))
    conn.commit()
    task_id = cur.lastrowid
    conn.close()
    return jsonify({'ok': True, 'id': task_id})


@prospects_bp.route('/tasks/<int:tid>/complete', methods=['PUT'])
def complete_task(tid):
    conn = get_db()
    conn.execute("""
        UPDATE tasks SET completada=1, completada_at=datetime('now','localtime')
        WHERE id=?
    """, (tid,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@prospects_bp.route('/tasks/<int:tid>/reagendar', methods=['PUT'])
def reagendar_task(tid):
    data = request.json
    conn = get_db()
    conn.execute("""
        UPDATE tasks SET fecha=?, hora=?, nota_reagenda=?,
        completada=0, completada_at=NULL
        WHERE id=?
    """, (data.get('fecha'), data.get('hora',''), data.get('nota',''), tid))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@prospects_bp.route('/<int:prospect_id>', methods=['DELETE'])
def delete_prospect(prospect_id):
    """Elimina un prospecto de Interesados"""
    conn = get_db()
    # Eliminar tareas asociadas
    conn.execute('DELETE FROM tasks WHERE prospect_id=?', (prospect_id,))
    # Eliminar prospecto
    conn.execute('DELETE FROM prospects WHERE id=?', (prospect_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


# ─── CRM ESTADOS Y ACTIVIDAD ─────────────────────────────────

@prospects_bp.route('/<int:prospect_id>/estado', methods=['PUT'])
def update_prospect_estado(prospect_id):
    """Actualiza estado del prospecto y sincroniza con leads"""
    data = request.json or {}
    estado = data.get('estado', '')
    motivo_perdida = data.get('motivo_perdida', '')
    notas = data.get('notas', '')

    # Mapeo estado prospecto -> estado lead
    ESTADO_LEAD_MAP = {
        'en_seguimiento': 'interesado',
        'reunion_agendada': 'quiere_reunion',
        'cerrado': 'cerrado',
        'no_logrado': 'no_interesado',
        'sin_respuesta': 'enviado'
    }

    conn = get_db()
    conn.execute(
        "UPDATE prospects SET estado=?, updated_at=datetime('now','localtime') WHERE id=?",
        (estado, prospect_id)
    )

    # Registrar actividad
    conn.execute("""
        INSERT INTO actividad_prospects (prospect_id, tipo, resultado, notas, motivo_perdida)
        VALUES (?, 'cambio_estado', ?, ?, ?)
    """, (prospect_id, estado, notas, motivo_perdida))

    # Sincronizar con lead
    prospect = conn.execute(
        'SELECT lead_id FROM prospects WHERE id=?', (prospect_id,)
    ).fetchone()

    if prospect and prospect['lead_id']:
        lead_status = ESTADO_LEAD_MAP.get(estado, 'interesado')
        nota_lead = f"Desde Interesados: {estado}" + (f" - {motivo_perdida}" if motivo_perdida else "")
        conn.execute("""
            INSERT INTO lead_status (lead_id, status, notes, updated_at)
            VALUES (?, ?, ?, datetime('now','localtime'))
            ON CONFLICT(lead_id) DO UPDATE SET
                status=excluded.status,
                notes=excluded.notes,
                updated_at=excluded.updated_at
        """, (prospect['lead_id'], lead_status, nota_lead))
        
        # Si cerrado, crear seller automaticamente
        if estado == 'cerrado':
            lead = conn.execute(
                'SELECT name, phone, rubro, categoria FROM leads WHERE id=?',
                (prospect['lead_id'],)
            ).fetchone()
            if lead:
                prospect_data = conn.execute(
                    'SELECT name, negocio FROM prospects WHERE id=?',
                    (prospect_id,)
                ).fetchone()
                contact_name = prospect_data['name'] if prospect_data else lead['name']
                existing_seller = conn.execute(
                    'SELECT id FROM sellers WHERE phone=?', (lead['phone'],)
                ).fetchone()
                if not existing_seller:
                    conn.execute("""
                        INSERT INTO sellers (name, phone, rubro, categoria, pos_type, created_at)
                        VALUES (?, ?, ?, ?, 'Point Pro 2', datetime('now','localtime'))
                    """, (contact_name, lead['phone'], lead['rubro'], lead['categoria']))
        
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@prospects_bp.route('/<int:prospect_id>/actividad', methods=['GET'])
def get_actividad(prospect_id):
    """Retorna historial de actividad de un prospecto"""
    conn = get_db()
    rows = conn.execute("""
        SELECT id, tipo, resultado, notas, motivo_perdida, created_at
        FROM actividad_prospects
        WHERE prospect_id=?
        ORDER BY created_at DESC
    """, (prospect_id,)).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@prospects_bp.route('/<int:prospect_id>/actividad', methods=['POST'])
def add_actividad(prospect_id):
    """Agrega una actividad al historial del prospecto"""
    data = request.json or {}
    conn = get_db()
    conn.execute("""
        INSERT INTO actividad_prospects (prospect_id, tipo, resultado, notas, motivo_perdida)
        VALUES (?, ?, ?, ?, ?)
    """, (prospect_id, data.get('tipo',''), data.get('resultado',''),
          data.get('notas',''), data.get('motivo_perdida','')))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@prospects_bp.route('/kpis', methods=['GET'])
def get_prospects_kpis():
    """KPIs de interesados para medicion"""
    conn = get_db()

    # Total por estado
    por_estado = conn.execute("""
        SELECT estado, COUNT(*) as total
        FROM prospects GROUP BY estado
    """).fetchall()

    # Motivos de perdida
    motivos = conn.execute("""
        SELECT motivo_perdida, COUNT(*) as total
        FROM actividad_prospects
        WHERE motivo_perdida IS NOT NULL AND motivo_perdida != ''
        GROUP BY motivo_perdida ORDER BY total DESC
    """).fetchall()

    # Tasa de cierre
    total = conn.execute("SELECT COUNT(*) FROM prospects").fetchone()[0]
    cerrados = conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE estado='cerrado'"
    ).fetchone()[0]
    no_logrados = conn.execute(
        "SELECT COUNT(*) FROM prospects WHERE estado='no_logrado'"
    ).fetchone()[0]

    # Tiempo promedio hasta cierre
    tiempo_cierre = conn.execute("""
        SELECT AVG(CAST((julianday(updated_at) - julianday(created_at)) AS INTEGER)) as dias_promedio
        FROM prospects WHERE estado='cerrado'
    """).fetchone()[0]

    # Competencia mas frecuente
    competencia = conn.execute("""
        SELECT competencia, COUNT(*) as total
        FROM prospects
        WHERE competencia IS NOT NULL AND competencia != ''
        GROUP BY competencia ORDER BY total DESC LIMIT 5
    """).fetchall()

    conn.close()
    return jsonify({
        'total': total,
        'cerrados': cerrados,
        'no_logrados': no_logrados,
        'tasa_cierre': round(cerrados/total*100, 1) if total > 0 else 0,
        'dias_promedio_cierre': round(tiempo_cierre or 0, 1),
        'por_estado': [dict(r) for r in por_estado],
        'motivos_perdida': [dict(r) for r in motivos],
        'competencia': [dict(r) for r in competencia]
    })


@prospects_bp.route('/reciclables', methods=['GET'])
def get_reciclables():
    """
    Busca prospects no_logrado cuyo motivo_perdida coincide con palabras clave.
    GET /api/prospects/reciclables?q=precio,comision
    Returns lista de prospects con info de contacto + motivo original.
    """
    q = request.args.get('q', '').strip()
    conn = get_db()

    if not q:
        # Sin filtro: devolver todos los no_logrado con motivo
        rows = conn.execute("""
            SELECT p.id, p.name, p.phone, p.negocio, p.rubro, p.categoria, p.comuna,
                   p.competencia, p.notas, p.updated_at,
                   ap.motivo_perdida, ap.notas as notas_actividad, ap.created_at as fecha_perdida
            FROM prospects p
            JOIN actividad_prospects ap ON p.id = ap.prospect_id
            WHERE p.estado = 'no_logrado'
              AND ap.motivo_perdida IS NOT NULL AND ap.motivo_perdida != ''
            ORDER BY ap.created_at DESC
            LIMIT 100
        """).fetchall()
    else:
        # Construir cláusula LIKE para cada término (separados por coma o espacio)
        terms = [t.strip() for t in q.replace(',', ' ').split() if t.strip()]
        if not terms:
            conn.close()
            return jsonify([])
        like_clauses = ' OR '.join(['ap.motivo_perdida LIKE ?' for _ in terms])
        params = [f'%{t}%' for t in terms]
        rows = conn.execute(f"""
            SELECT p.id, p.name, p.phone, p.negocio, p.rubro, p.categoria, p.comuna,
                   p.competencia, p.notas, p.updated_at,
                   ap.motivo_perdida, ap.notas as notas_actividad, ap.created_at as fecha_perdida
            FROM prospects p
            JOIN actividad_prospects ap ON p.id = ap.prospect_id
            WHERE p.estado = 'no_logrado'
              AND ap.motivo_perdida IS NOT NULL AND ap.motivo_perdida != ''
              AND ({like_clauses})
            ORDER BY ap.created_at DESC
            LIMIT 100
        """, params).fetchall()

    conn.close()
    return jsonify([dict(r) for r in rows])


@prospects_bp.route('/sync-lead-status', methods=['POST'])
def sync_lead_status():
    """
    Sincroniza todos los prospects con lead_id a lead_status.
    Usa el estado actual del prospect como referencia.
    Útil para reparar registros existentes.
    """
    ESTADO_LEAD_MAP = {
        'en_seguimiento': 'interesado',
        'reunion_agendada': 'quiere_reunion',
        'cerrado': 'cerrado',
        'no_logrado': 'no_interesado',
        'sin_respuesta': 'enviado'
    }

    conn = get_db()

    # Obtener todos los prospects con lead_id
    prospects = conn.execute(
        "SELECT id, lead_id, estado FROM prospects WHERE lead_id IS NOT NULL"
    ).fetchall()

    synced = 0
    for p in prospects:
        ls = ESTADO_LEAD_MAP.get(p['estado'], 'interesado')
        conn.execute("""
            INSERT INTO lead_status (lead_id, status, notes, updated_at)
            VALUES (?, ?, 'Sincronizado desde Gestión', datetime('now','localtime'))
            ON CONFLICT(lead_id) DO UPDATE SET
                status=excluded.status,
                notes=excluded.notes,
                updated_at=excluded.updated_at
        """, (p['lead_id'], ls))
        synced += 1

    conn.commit()
    conn.close()

    return jsonify({'ok': True, 'synced': synced})
