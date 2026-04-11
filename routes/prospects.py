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
        INSERT INTO prospects (lead_id, name, phone, negocio, rubro, categoria, comuna, competencia, procedencia, notas)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        data.get('lead_id'), data.get('name'), data.get('phone'),
        data.get('negocio'), data.get('rubro'), data.get('categoria'),
        data.get('comuna'), data.get('competencia', ''),
        data.get('procedencia', 'Online'), data.get('notas', '')
    ))
    conn.commit()
    prospect_id = cur.lastrowid
    conn.close()
    return jsonify({'ok': True, 'id': prospect_id})


@prospects_bp.route('/<int:pid>', methods=['PUT'])
def update_prospect(pid):
    data = request.json
    conn = get_db()
    conn.execute("""
        UPDATE prospects SET
            competencia=?, procedencia=?, notas=?,
            updated_at=datetime('now','localtime')
        WHERE id=?
    """, (data.get('competencia',''), data.get('procedencia','Online'),
          data.get('notas',''), pid))
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
