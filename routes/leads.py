"""
Rutas Flask: Leads
"""
from flask import Blueprint, request, jsonify
from database import get_db, update_lead_status, add_opt_out, clean_phone

leads_bp = Blueprint('leads', __name__)


@leads_bp.route('/', methods=['GET'])
def get_leads():
    conn = get_db()
    status_filter = request.args.get('status')
    comuna_filter = request.args.get('comuna')
    rubro_filter = request.args.get('rubro')
    search = request.args.get('q')

    query = '''
        SELECT l.id, l.name, l.phone, l.comuna, l.rubro, l.categoria, l.address,
               l.fast_ok, l.created_at, l.updated_at, l.source,
               ls.status, ls.notes, ls.optout_motivo,
               m.sent_at, m.opened_at,
               seg24.sent_at as seguimiento_24h_fecha,
               CASE WHEN seg24.lead_id IS NOT NULL THEN 1 ELSE 0 END as seguimiento_24h,
               seg72.sent_at as seguimiento_72h_fecha,
               CASE WHEN seg72.lead_id IS NOT NULL THEN 1 ELSE 0 END as seguimiento_72h
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        LEFT JOIN (
            SELECT lead_id, sent_at, opened_at, message_type
            FROM messages
            WHERE message_type IN ('prospecting','manual')
            GROUP BY lead_id
        ) m ON l.id = m.lead_id
        LEFT JOIN (
            SELECT lead_id, sent_at FROM messages
            WHERE message_type = 'seguimiento_24h' AND status = 'sent'
            GROUP BY lead_id
        ) seg24 ON l.id = seg24.lead_id
        LEFT JOIN (
            SELECT lead_id, sent_at FROM messages
            WHERE message_type = 'seguimiento_72h' AND status = 'sent'
            GROUP BY lead_id
        ) seg72 ON l.id = seg72.lead_id
        WHERE 1=1
    '''
    params = []

    if status_filter and status_filter != 'todos':
        query += ' AND ls.status = ?'
        params.append(status_filter)
    if comuna_filter:
        query += ' AND l.comuna = ?'
        params.append(comuna_filter)
    if rubro_filter:
        query += ' AND l.rubro = ?'
        params.append(rubro_filter)
    if search:
        query += ' AND (l.name LIKE ? OR l.comuna LIKE ? OR l.rubro LIKE ?)'
        s = f'%{search}%'
        params += [s, s, s]

    query += ' ORDER BY l.updated_at DESC LIMIT 500'

    rows = conn.execute(query, params).fetchall()
    conn.close()

    from rubros_config import RUBROS, RUBRO_LABEL_TO_KEY
    result = []
    for row in rows:
        r = dict(row)
        # Agregar categoria segun rubro
        rk = RUBRO_LABEL_TO_KEY.get((r.get('rubro') or '').lower(), r.get('rubro',''))
        r['categoria'] = RUBROS.get(rk, {}).get('categoria', '')
        # Normalizar estado no_enviado para metricas
        if r.get('status') == 'no_enviado':
            r['status_display'] = 'No enviado'
        result.append(r)
    return jsonify(result)


@leads_bp.route('/<int:lead_id>/status', methods=['PUT'])
def update_status(lead_id):
    data = request.json
    status = data.get('status')
    notes = data.get('notes')
    optout_motivo = data.get('optout_motivo', '')
    if not status:
        return jsonify({'error': 'status required'}), 400
    conn = get_db()
    lead = conn.execute('SELECT id, name, phone, rubro, comuna FROM leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()
    if not lead:
        return jsonify({'error': 'lead not found'}), 404
    lead = dict(lead)
    update_lead_status(lead['phone'], status, notes, optout_motivo=optout_motivo)

    # Enviar WhatsApp automatico cuando opt-out motivo = Tiene MP
    if (status in ('opt_out', 'no_interesado')) and optout_motivo == 'Tiene MP':
        import threading
        def _send_tiene_mp():
            from whatsapp.sender_desktop import get_sender
            from database import get_db as _db
            msg = (
                "Qué excelente noticia que ya seas parte de Mercado Pago. "
                "Te dejo mi contacto: si en el futuro conoces a algún colega o amigo que necesite "
                "sumar una máquina a su negocio, ¡feliz de ayudarle con los mejores beneficios! "
                "Además, cuenta con mi apoyo desde ya. Si alguna vez necesitas orientación o ayuda "
                "con tus equipos o tu cuenta, no dudes en escribirme. "
                "¡Mucho éxito y excelentes ventas!"
            )
            sender = get_sender()
            if not sender._is_logged_in:
                sender.start()
            result = sender.send_message(lead['phone'], msg, None)
            conn2 = _db()
            conn2.execute('''
                INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
                VALUES (?, ?, 'tiene_mp', ?, datetime('now','localtime'), ?, ?)
            ''', (lead_id, lead['phone'],
                  'sent' if result['success'] else 'failed',
                  lead.get('rubro',''), lead.get('comuna','')))
            conn2.commit()
            conn2.close()
        t = threading.Thread(target=_send_tiene_mp)
        t.daemon = True
        t.start()

    return jsonify({'ok': True})


@leads_bp.route('/<int:lead_id>/opt-out', methods=['POST'])
def opt_out(lead_id):
    conn = get_db()
    lead = conn.execute('SELECT phone FROM leads WHERE id = ?', (lead_id,)).fetchone()
    conn.close()
    if not lead:
        return jsonify({'error': 'lead not found'}), 404
    add_opt_out(lead['phone'], 'usuario solicitó')
    update_lead_status(lead['phone'], 'opt_out')
    return jsonify({'ok': True})


@leads_bp.route('/stats/comunas', methods=['GET'])
def stats_comunas():
    conn = get_db()
    rows = conn.execute('''
        SELECT comuna, COUNT(*) as total
        FROM leads GROUP BY comuna ORDER BY total DESC LIMIT 20
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@leads_bp.route('/stats/rubros', methods=['GET'])
def stats_rubros():
    conn = get_db()
    rows = conn.execute('''
        SELECT rubro, COUNT(*) as total
        FROM leads GROUP BY rubro ORDER BY total DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@leads_bp.route('/<int:lead_id>/seguimiento', methods=['POST'])
def send_seguimiento_manual(lead_id):
    """Envia mensaje de seguimiento manual a un lead"""
    conn = get_db()
    lead = conn.execute('''
        SELECT l.id, l.name, l.phone, l.rubro, l.comuna,
               m.sent_at,
               CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
        FROM leads l
        LEFT JOIN messages m ON l.id = m.lead_id AND m.status = 'sent'
        WHERE l.id = ?
        ORDER BY m.sent_at DESC LIMIT 1
    ''', (lead_id,)).fetchone()

    if not lead:
        conn.close()
        return jsonify({'error': 'Lead no encontrado'}), 404

    lead = dict(lead)
    horas = lead.get('horas') or 0

    # Determinar que mensaje enviar segun horas
    if horas >= 72:
        msg_template = "Hola {nombre}! Te escribo cortito para no quitarte tiempo ni ser invasivo. Si mas adelante te animas a probar, me avisas y lo revisamos. Que tengas un lindo dia. Saludos"
        tipo = '72h'
    else:
        msg_template = "Hola {nombre}! Como estas? Te escribo rapidito para saber si pudiste darle una mirada a la imagen que te mande el otro dia. Me encantaria que comparemos juntos. Avisame si tienes un tiempo para llamarte, la idea es ver de forma transparente si realmente te conviene el cambio. Un abrazo"
        tipo = '24h'

    mensaje = msg_template.format(nombre=lead['name'])
    conn.close()

    import threading
    def _send():
        from whatsapp.sender_desktop import get_sender
        from database import get_db as _db
        sender = get_sender()
        if not sender._is_logged_in:
            sender.start()
        result = sender.send_message(lead['phone'], mensaje, None)
        conn2 = _db()
        status_msg = 'sent' if result['success'] else 'failed'
        conn2.execute('''
            INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
            VALUES (?, ?, ?, ?, datetime('now','localtime'), ?, ?)
        ''', (lead_id, lead['phone'], f'seguimiento_{tipo}',
               status_msg,
               lead.get('rubro',''), lead.get('comuna','')))
        # Actualizar columna seguimiento en leads para mostrar icono
        if result['success']:
            if tipo == '24h':
                conn2.execute(
                    "UPDATE leads SET seguimiento_24h=1, seguimiento_24h_fecha=datetime('now','localtime') WHERE id=?",
                    (lead_id,)
                )
            elif tipo == '72h':
                conn2.execute(
                    "UPDATE leads SET seguimiento_72h=1, seguimiento_72h_fecha=datetime('now','localtime') WHERE id=?",
                    (lead_id,)
                )
        conn2.commit()
        conn2.close()

    t = threading.Thread(target=_send)
    t.daemon = True
    t.start()

    return jsonify({'ok': True, 'message': f'Seguimiento enviado a {lead["name"]}', 'tipo': tipo})


@leads_bp.route('/import', methods=['POST'])
def import_leads():
    """Importa leads desde Excel via JS"""
    from database import get_db
    data = request.json
    leads_data = data.get('leads', [])

    RUBRO_CATEGORIA = {
        'almacen': 'Comercio de Barrio Diario',
        'bazar': 'Retail Especializado y Hogar',
        'botilleria': 'Comercio de Alta Demanda Fin de Semana',
        'cafeteria': 'Gastronomia y Comida Rapida',
        'carniceria': 'Comercio de Alta Demanda Fin de Semana',
        'clinica_dental': 'Servicios de Alto Ticket',
        'emporio': 'Comercio de Barrio Diario',
        'farmacia': 'Salud y Farmacia',
        'ferreteria': 'Retail Especializado y Hogar',
        'fruteria': 'Comercio de Barrio Diario',
        'fuente_de_soda': 'Gastronomia y Comida Rapida',
        'gimnasio': 'Membresias y Entrenamientos',
        'lavanderia': 'Servicios Personales Diario',
        'libreria': 'Retail Especializado y Hogar',
        'minimarket': 'Comercio de Barrio Diario',
        'muebleria': 'Retail Especializado y Hogar',
        'panaderia': 'Comercio de Barrio Diario',
        'peluqueria': 'Servicios Personales Diario',
        'pizzeria': 'Gastronomia y Comida Rapida',
        'sandwicheria': 'Gastronomia y Comida Rapida',
        'spa': 'Servicios de Alto Ticket',
        'sushi': 'Gastronomia y Comida Rapida',
        'taller': 'Servicios de Alto Ticket',
        'verduleria': 'Comercio de Barrio Diario',
        'veterinaria': 'Servicios de Alto Ticket',
    }

    conn = get_db()
    importados = 0
    duplicados = 0
    ids_importados = []

    for lead in leads_data:
        phone = lead.get('phone', '').strip()
        name  = lead.get('name', '').strip()
        if not phone or not name:
            continue

        # Verificar duplicado por telefono
        existing = conn.execute(
            'SELECT id FROM leads WHERE phone = ?', (phone,)
        ).fetchone()

        if existing:
            duplicados += 1
            continue

        rubro    = lead.get('rubro', '').strip()
        comuna   = lead.get('comuna', '').strip()
        categoria = RUBRO_CATEGORIA.get(rubro, '')

        cur = conn.execute(
            'INSERT INTO leads (name, phone, comuna, rubro, categoria) VALUES (?, ?, ?, ?, ?)',
            (name, phone, comuna, rubro, categoria)
        )
        lead_id = cur.lastrowid

        # Estado no_enviado por defecto
        conn.execute(
            "INSERT INTO lead_status (lead_id, status, updated_at) VALUES (?, 'no_enviado', datetime('now','localtime'))",
            (lead_id,)
        )
        importados += 1
        ids_importados.append(lead_id)

    conn.commit()
    conn.close()

    # Registrar importacion en BD
    if importados > 0:
        import json as _json
        conn.execute(
            "INSERT INTO importaciones (filename, total_leads, importados, duplicados, lead_ids) VALUES (?, ?, ?, ?, ?)",
            (data.get('filename', 'archivo.xlsx'), len(leads_data), importados, duplicados,
             _json.dumps(ids_importados))
        )
        conn.commit()

    return jsonify({'ok': True, 'importados': importados, 'duplicados': duplicados, 'ids': ids_importados})


@leads_bp.route('/<int:lead_id>/update-rubro', methods=['PUT'])
def update_rubro(lead_id):
    data = request.json
    rubro = data.get('rubro', '')
    categoria = data.get('categoria', '')
    rubro_original = data.get('rubro_original', '')
    aplicar_todos = data.get('aplicar_todos', False)
    conn = get_db()
    actualizados = 0

    if aplicar_todos and rubro_original:
        # Actualizar todos los leads con el mismo rubro original
        cur = conn.execute(
            'UPDATE leads SET rubro=?, categoria=? WHERE rubro=?',
            (rubro, categoria, rubro_original)
        )
        actualizados = cur.rowcount
    else:
        conn.execute(
            'UPDATE leads SET rubro=?, categoria=? WHERE id=?',
            (rubro, categoria, lead_id)
        )
        actualizados = 1

    # Si es rubro nuevo, registrar mensaje personalizado en config
    es_nuevo = data.get('es_nuevo', False)
    if es_nuevo and rubro and categoria:
        msg_nuevo = "Hola {nombre}, soy Sebastian Pinto, ayer pase por fuera de tu negocio y creo que Mercado Pago puede ser una gran alternativa. Mira, te dejo una imagen de referencia en lo que te podriamos aportar. Avisame si te parece, y evaluamos en funcion de tu actual proveedor de pagos. Saludos"
        conn.execute(
            "INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)",
            (f'mensaje_rubro_{rubro}', msg_nuevo)
        )

    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'actualizados': actualizados})


@leads_bp.route('/anular-importacion', methods=['POST'])
def anular_importacion():
    data = request.json
    ids = data.get('ids', [])
    if not ids:
        return jsonify({'error': 'No ids provided'}), 400
    conn = get_db()
    eliminados = 0
    for lead_id in ids:
        conn.execute('DELETE FROM lead_status WHERE lead_id = ?', (lead_id,))
        conn.execute('DELETE FROM leads WHERE id = ?', (lead_id,))
        eliminados += 1
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'eliminados': eliminados})


@leads_bp.route('/importaciones', methods=['GET'])
def get_importaciones():
    conn = get_db()
    rows = conn.execute(
        "SELECT id, filename, total_leads, importados, duplicados, lead_ids, created_at FROM importaciones ORDER BY created_at DESC"
    ).fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@leads_bp.route('/importaciones/<int:imp_id>', methods=['DELETE'])
def delete_importacion(imp_id):
    import json as _json
    conn = get_db()
    imp = conn.execute("SELECT lead_ids FROM importaciones WHERE id=?", (imp_id,)).fetchone()
    if not imp:
        conn.close()
        return jsonify({'error': 'No encontrado'}), 404
    
    eliminados = 0
    try:
        ids = _json.loads(imp['lead_ids'] or '[]')
        for lid in ids:
            conn.execute('DELETE FROM lead_status WHERE lead_id=?', (lid,))
            conn.execute('DELETE FROM leads WHERE id=?', (lid,))
            eliminados += 1
    except:
        pass
    
    conn.execute('DELETE FROM importaciones WHERE id=?', (imp_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'eliminados': eliminados})


@leads_bp.route('/rubros-personalizados', methods=['GET'])
def get_rubros_personalizados():
    """Retorna rubros personalizados guardados en config"""
    conn = get_db()
    rows = conn.execute(
        "SELECT key, value FROM config WHERE key LIKE 'mensaje_rubro_%'"
    ).fetchall()
    conn.close()
    rubros = [r['key'].replace('mensaje_rubro_', '') for r in rows]
    return jsonify({'rubros': rubros})


@leads_bp.route('/seguimientos-pendientes', methods=['GET'])
def get_seguimientos_pendientes():
    """Retorna leads con seguimiento 24h y 72h pendientes"""
    conn = get_db()
    
    # Leads enviados hace mas de 24h sin seguimiento 24h
    pendientes_24h = conn.execute("""
        SELECT l.id, l.name, l.phone, l.rubro,
               CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
        FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        JOIN messages m ON l.id = m.lead_id AND m.message_type = 'prospecting' AND m.status = 'sent'
        LEFT JOIN messages m24 ON l.id = m24.lead_id AND m24.message_type = 'seguimiento_24h'
        WHERE ls.status = 'enviado'
        AND m24.id IS NULL
        AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= 24
        AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) < 72
        GROUP BY l.id
        ORDER BY horas DESC
        LIMIT 10
    """).fetchall()

    # Leads enviados hace mas de 72h sin seguimiento 72h
    pendientes_72h = conn.execute("""
        SELECT l.id, l.name, l.phone, l.rubro,
               CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) as horas
        FROM leads l
        JOIN lead_status ls ON l.id = ls.lead_id
        JOIN messages m ON l.id = m.lead_id AND m.message_type = 'prospecting' AND m.status = 'sent'
        LEFT JOIN messages m72 ON l.id = m72.lead_id AND m72.message_type = 'seguimiento_72h'
        WHERE ls.status = 'enviado'
        AND m72.id IS NULL
        AND CAST((julianday('now','localtime') - julianday(m.sent_at)) * 24 AS INTEGER) >= 72
        GROUP BY l.id
        ORDER BY horas DESC
        LIMIT 10
    """).fetchall()

    conn.close()
    return jsonify({
        'pendientes_24h': [dict(r) for r in pendientes_24h],
        'pendientes_72h': [dict(r) for r in pendientes_72h]
    })


@leads_bp.route('/wa-actividad', methods=['GET'])
def get_wa_actividad():
    """Actividad WA por día — últimos 7 días (prospección + seguimientos)"""
    conn = get_db()
    rows = conn.execute("""
        SELECT
            date(sent_at) as fecha,
            SUM(CASE WHEN message_type IN ('prospecting','manual') THEN 1 ELSE 0 END) as prospec,
            SUM(CASE WHEN message_type = 'seguimiento_24h'          THEN 1 ELSE 0 END) as seg_24h,
            SUM(CASE WHEN message_type = 'seguimiento_72h'          THEN 1 ELSE 0 END) as seg_72h
        FROM messages
        WHERE status = 'sent'
          AND date(sent_at) >= date('now','localtime','-6 days')
        GROUP BY date(sent_at)
        ORDER BY fecha DESC
    """).fetchall()
    conn.close()
    return jsonify({'dias': [dict(r) for r in rows]})


@leads_bp.route('/wa-actividad/export', methods=['GET'])
def export_wa_actividad():
    """Exporta detalle WA de una fecha (o últimos 7 días) como Excel."""
    try:
        from flask import Response
        import io, openpyxl
        from openpyxl.styles import Font, PatternFill, Alignment
        from openpyxl.utils import get_column_letter

        fecha = request.args.get('fecha')   # YYYY-MM-DD opcional
        conn  = get_db()

        base_q = """
            SELECT m.sent_at, m.message_type, m.status, m.rubro, m.phone,
                   m.error_detail, l.name as negocio, l.comuna
            FROM messages m
            LEFT JOIN leads l ON m.lead_id = l.id
            WHERE m.message_type IN ('prospecting','manual','seguimiento_24h','seguimiento_72h')
        """
        if fecha:
            rows = conn.execute(base_q + " AND date(m.sent_at) = ? ORDER BY m.sent_at", (fecha,)).fetchall()
            fname = f'wa_{fecha}.xlsx'
        else:
            rows = conn.execute(base_q + " AND date(m.sent_at) >= date('now','localtime','-6 days') ORDER BY m.sent_at DESC", ()).fetchall()
            fname = 'wa_actividad_7dias.xlsx'
        conn.close()
    except Exception as e:
        conn.close()
        return jsonify({'error': f'Error en consulta: {str(e)}'}), 500

    TIPO_MAP = {
        'prospecting':    'Prospección',
        'manual':         'Prospección manual',
        'seguimiento_24h':'Seguimiento 24h',
        'seguimiento_72h':'Seguimiento 72h',
    }
    CAT_MAP = {
        'prospecting':    'Prospección',
        'manual':         'Prospección',
        'seguimiento_24h':'Seguimiento',
        'seguimiento_72h':'Seguimiento',
    }
    STATUS_MAP = {
        'sent':             'Enviado',
        'failed':           'No enviado',
        'phone_not_exists': 'Número no existe',
    }

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = 'Actividad WA'

    # Encabezado
    headers = ['Fecha Envío', 'Tipo', 'Categoría', 'Rubro', 'Negocio', 'Teléfono', 'Comuna', 'Estado', 'Error']
    hdr_fill = PatternFill('solid', fgColor='009EE3')
    hdr_font = Font(bold=True, color='FFFFFF')
    for col, h in enumerate(headers, 1):
        cell = ws.cell(row=1, column=col, value=h)
        cell.fill = hdr_fill
        cell.font = hdr_font
        cell.alignment = Alignment(horizontal='center')

    try:
        # Colores por estado
        fill_ok  = PatternFill('solid', fgColor='E8F5E9')
        fill_err = PatternFill('solid', fgColor='FFEBEE')

        # Datos
        for row_idx, r in enumerate(rows, 2):
            estado = STATUS_MAP.get(r['status'], r['status'] or 'Enviado')
            error  = r['error_detail'] or ''
            # Convertir sent_at a string si no lo es (por si acaso es datetime)
            sent_at_str = str(r['sent_at']) if r['sent_at'] else ''
            ws.append([
                sent_at_str,
                TIPO_MAP.get(r['message_type'], r['message_type']),
                CAT_MAP.get(r['message_type'], ''),
                r['rubro'] or '',
                r['negocio'] or '',
                r['phone'] or '',
                r['comuna'] or '',
                estado,
                error,
            ])
            # Color verde/rojo en columna Estado
            fill = fill_ok if r['status'] == 'sent' else fill_err
            ws.cell(row=row_idx, column=8).fill = fill
            ws.cell(row=row_idx, column=8).font = Font(
                color='1B5E20' if r['status'] == 'sent' else 'B71C1C', bold=True
            )

        # Ancho columnas
        col_widths = [20, 20, 14, 18, 30, 16, 18, 14, 40]
        for i, w in enumerate(col_widths, 1):
            ws.column_dimensions[get_column_letter(i)].width = w

        buf = io.BytesIO()
        wb.save(buf)
        buf.seek(0)
        return Response(
            buf.getvalue(),
            mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
            headers={'Content-Disposition': f'attachment; filename="{fname}"'}
        )
    except Exception as e:
        return jsonify({'error': f'Error generando Excel: {str(e)}'}), 500


@leads_bp.route('/<int:lead_id>/seguimiento-tipo', methods=['POST'])
def send_seguimiento_tipo(lead_id):
    """Envia mensaje de seguimiento especifico 24h o 72h"""
    data = request.json or {}
    tipo = data.get('tipo', '24h')
    
    conn = get_db()
    lead = conn.execute(
        'SELECT id, name, phone, rubro, comuna FROM leads WHERE id=?', (lead_id,)
    ).fetchone()
    conn.close()
    
    if not lead:
        return jsonify({'error': 'Lead no encontrado'}), 404
    
    lead = dict(lead)
    
    MSG_24H = "Hola {nombre}! Como estas? Te escribo rapidito para saber si pudiste darle una mirada a la imagen que te mande el otro dia. Me encantaria que comparemos juntos. Avisame si tienes un tiempo para llamarte, la idea es ver de forma transparente si realmente te conviene el cambio. Un abrazo"
    MSG_72H = "Hola {nombre}! Te escribo cortito para no quitarte tiempo ni ser invasivo. Si mas adelante te animas a probar, me avisas y lo revisamos. Que tengas un lindo dia. Saludos"
    
    mensaje = (MSG_24H if tipo == '24h' else MSG_72H).format(nombre=lead['name'])
    
    import threading
    def _send():
        from whatsapp.sender_desktop import get_sender
        from database import get_db as _db
        sender = get_sender()
        if not sender._is_logged_in:
            sender.start()
        result = sender.send_message(lead['phone'], mensaje, None)
        conn2 = _db()
        conn2.execute("""
            INSERT INTO messages (lead_id, phone, message_type, status, sent_at, rubro, comuna)
            VALUES (?, ?, ?, ?, datetime('now','localtime'), ?, ?)
        """, (lead_id, lead['phone'], f'seguimiento_{tipo}',
              'sent' if result['success'] else 'failed',
              lead.get('rubro',''), lead.get('comuna','')))
        if result['success']:
            if tipo == '24h':
                conn2.execute(
                    "UPDATE leads SET seguimiento_24h=1, seguimiento_24h_fecha=datetime('now','localtime') WHERE id=?",
                    (lead_id,)
                )
            else:
                conn2.execute(
                    "UPDATE leads SET seguimiento_72h=1, seguimiento_72h_fecha=datetime('now','localtime') WHERE id=?",
                    (lead_id,)
                )
        conn2.commit()
        conn2.close()
    
    t = threading.Thread(target=_send)
    t.daemon = True
    t.start()
    
    return jsonify({'ok': True, 'tipo': tipo})


@leads_bp.route('/<int:lead_id>/address', methods=['GET'])
def get_lead_address(lead_id):
    conn = get_db()
    lead = conn.execute('SELECT address FROM leads WHERE id=?', (lead_id,)).fetchone()
    conn.close()
    if not lead:
        return jsonify({'address': ''})
    return jsonify({'address': lead['address'] or ''})


@leads_bp.route('/<int:lead_id>/address', methods=['PUT'])
def update_lead_address(lead_id):
    data = request.get_json() or {}
    address = data.get('address', '').strip()
    conn = get_db()
    conn.execute('UPDATE leads SET address=? WHERE id=?', (address, lead_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'address': address})
