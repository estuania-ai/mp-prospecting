"""
Rutas de autenticación: login, registro, logout, cambio de password.
Y el panel admin del TL para aprobar usuarios pendientes.
"""
from datetime import datetime
from flask import Blueprint, request, jsonify, render_template, redirect, url_for, flash, session
from flask_login import login_user, logout_user, login_required, current_user

from database import get_db
from auth import (
    User, hash_password, verify_password,
    validate_password_strength, validate_gmail,
    is_user_locked, register_failed_login, clear_failed_logins,
    requires_tl, MAX_FAILED_LOGINS, LOCKOUT_MINUTES, OWNER_EMAIL
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email = (request.form.get('email') or '').strip().lower()
        password = request.form.get('password') or ''

        # No revelamos si el email existe o no — mensaje genérico siempre
        generic_error = 'Email o contraseña incorrectos'

        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE email = ?', (email,)).fetchone()
        conn.close()

        if not row:
            flash(generic_error, 'error')
            return render_template('auth/login.html'), 401

        if is_user_locked(row):
            flash(f'Cuenta bloqueada por {LOCKOUT_MINUTES} min tras varios intentos fallidos. Espera o contacta al TL.', 'error')
            return render_template('auth/login.html'), 423

        if not verify_password(password, row['password_hash']):
            register_failed_login(row['id'])
            flash(generic_error, 'error')
            return render_template('auth/login.html'), 401

        if row['status'] == 'pending':
            flash('Tu cuenta está pendiente de aprobación por un Team Leader.', 'warning')
            return render_template('auth/login.html'), 403

        if row['status'] == 'disabled':
            flash('Tu cuenta está deshabilitada. Contacta al TL.', 'error')
            return render_template('auth/login.html'), 403

        # Login exitoso
        clear_failed_logins(row['id'])
        # Regenerar session id para evitar session fixation
        session.clear()
        user = User(row)
        login_user(user, remember=False)

        # Forzar cambio de password si nunca lo hizo
        if not user.password_changed:
            return redirect(url_for('auth.change_password'))

        return redirect(url_for('index'))

    return render_template('auth/login.html')


# ═══════════════════════════════════════════════════════════════
# REGISTRO (queda pending, TL aprueba)
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('index'))

    if request.method == 'POST':
        email    = (request.form.get('email') or '').strip().lower()
        username = (request.form.get('username') or '').strip()
        name     = (request.form.get('name') or '').strip()
        password = request.form.get('password') or ''
        password_confirm = request.form.get('password_confirm') or ''

        if not validate_gmail(email):
            flash('El email debe ser un Gmail válido (@gmail.com)', 'error')
            return render_template('auth/register.html')

        if not username or len(username) < 3:
            flash('El usuario debe tener al menos 3 caracteres', 'error')
            return render_template('auth/register.html')

        if not name:
            flash('Nombre es obligatorio', 'error')
            return render_template('auth/register.html')

        if password != password_confirm:
            flash('Las contraseñas no coinciden', 'error')
            return render_template('auth/register.html')

        ok, msg = validate_password_strength(password)
        if not ok:
            flash(msg, 'error')
            return render_template('auth/register.html')

        # Verificar duplicados
        conn = get_db()
        existing = conn.execute(
            'SELECT id FROM users WHERE email = ? OR username = ?', (email, username)
        ).fetchone()

        if existing:
            conn.close()
            # Mensaje genérico — no revelar si el email o user ya existe
            flash('No se pudo crear la cuenta. Verifica los datos.', 'error')
            return render_template('auth/register.html')

        # ── Lógica de roles iniciales ──
        # 1. Si el email es el OWNER_EMAIL configurado → automáticamente OWNER + activo
        # 2. Si es el primer usuario del sistema (bootstrap sin owner email) → TL activo
        # 3. Cualquier otro caso → pending, espera aprobación
        is_owner_email = (email == OWNER_EMAIL)
        first_user = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c'] == 0

        if is_owner_email:
            initial_role = 'owner'
            initial_status = 'active'
            password_changed = 1   # owner ya viene con su pwd que él mismo eligió
        elif first_user:
            initial_role = 'tl'
            initial_status = 'active'
            password_changed = 1
        else:
            initial_role = None
            initial_status = 'pending'
            password_changed = 0

        conn.execute('''
            INSERT INTO users (email, username, password_hash, name, role, status, password_changed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (email, username, hash_password(password), name, initial_role, initial_status, password_changed))
        conn.commit()
        conn.close()

        if is_owner_email:
            flash('Cuenta de Owner creada. Ya puedes iniciar sesión.', 'success')
        elif first_user:
            flash('Cuenta creada como TL inicial. Ya puedes iniciar sesión.', 'success')
        else:
            flash('Registro exitoso. Tu cuenta queda pendiente de aprobación por un Team Leader.', 'success')

        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


# ═══════════════════════════════════════════════════════════════
# LOGOUT
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/logout', methods=['GET', 'POST'])
@login_required
def logout():
    logout_user()
    session.clear()
    flash('Sesión cerrada.', 'info')
    return redirect(url_for('auth.login'))


# ═══════════════════════════════════════════════════════════════
# CAMBIO DE PASSWORD
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current = request.form.get('current_password') or ''
        new_pwd = request.form.get('new_password') or ''
        confirm = request.form.get('confirm_password') or ''

        # Validar password actual
        conn = get_db()
        row = conn.execute('SELECT password_hash FROM users WHERE id=?', (current_user.id,)).fetchone()
        conn.close()

        if not row or not verify_password(current, row['password_hash']):
            flash('Contraseña actual incorrecta', 'error')
            return render_template('auth/change_password.html')

        if new_pwd != confirm:
            flash('Las contraseñas nuevas no coinciden', 'error')
            return render_template('auth/change_password.html')

        ok, msg = validate_password_strength(new_pwd)
        if not ok:
            flash(msg, 'error')
            return render_template('auth/change_password.html')

        if new_pwd == current:
            flash('La nueva contraseña debe ser distinta a la actual', 'error')
            return render_template('auth/change_password.html')

        conn = get_db()
        conn.execute('UPDATE users SET password_hash=?, password_changed=1 WHERE id=?',
                     (hash_password(new_pwd), current_user.id))
        conn.commit()
        conn.close()

        flash('Contraseña actualizada correctamente.', 'success')
        return redirect(url_for('index'))

    return render_template('auth/change_password.html')


# ═══════════════════════════════════════════════════════════════
# ADMIN: lista de usuarios pendientes (solo TL)
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/admin/users', methods=['GET'])
@requires_tl
def admin_list_users():
    conn = get_db()
    rows = conn.execute('''
        SELECT id, email, username, name, role, status, created_at, last_login
        FROM users
        ORDER BY
            CASE status WHEN 'pending' THEN 0 WHEN 'active' THEN 1 ELSE 2 END,
            created_at DESC
    ''').fetchall()
    conn.close()
    return jsonify([dict(r) for r in rows])


@auth_bp.route('/admin/users/<int:user_id>/approve', methods=['POST'])
@requires_tl
def admin_approve_user(user_id):
    """
    Aprueba un usuario pendiente, asigna rol y (si es Sales) team_lead_id.
    Body: {role: 'tl'|'sales', team_lead_id: int? (requerido si role=sales)}
    """
    data = request.get_json() or {}
    role = (data.get('role') or '').strip().lower()
    team_lead_id = data.get('team_lead_id')

    if role not in ('tl', 'sales'):
        return jsonify({'error': 'Rol inválido (debe ser tl o sales)'}), 400

    conn = get_db()
    row = conn.execute('SELECT id, status FROM users WHERE id=?', (user_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if row['status'] != 'pending':
        conn.close()
        return jsonify({'error': f'Usuario ya está en estado: {row["status"]}'}), 400

    # Validar team_lead si es Sales
    if role == 'sales':
        if not team_lead_id:
            # Default: el TL/Owner que está aprobando
            team_lead_id = current_user.id
        else:
            # Verificar que team_lead_id corresponde a un TL u Owner activo
            tl_row = conn.execute(
                "SELECT id, role FROM users WHERE id=? AND status='active' AND role IN ('tl','owner')",
                (team_lead_id,)
            ).fetchone()
            if not tl_row:
                conn.close()
                return jsonify({'error': 'team_lead_id no corresponde a un TL/Owner activo'}), 400
    else:
        team_lead_id = None  # TLs no tienen team_lead

    conn.execute(
        'UPDATE users SET role=?, status="active", team_lead_id=? WHERE id=?',
        (role, team_lead_id, user_id)
    )
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'role': role, 'team_lead_id': team_lead_id})


@auth_bp.route('/admin/users/<int:user_id>/disable', methods=['POST'])
@requires_tl
def admin_disable_user(user_id):
    """Deshabilita un usuario (no se puede deshabilitar a sí mismo)."""
    if user_id == current_user.id:
        return jsonify({'error': 'No podés deshabilitarte a ti mismo'}), 400
    conn = get_db()
    conn.execute('UPDATE users SET status="disabled" WHERE id=?', (user_id,))
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@auth_bp.route('/admin/users/<int:user_id>/role', methods=['POST'])
@requires_tl
def admin_change_role(user_id):
    """Cambia rol de un usuario activo (TL ↔ Sales)."""
    if user_id == current_user.id:
        return jsonify({'error': 'No podés cambiar tu propio rol'}), 400
    data = request.get_json() or {}
    role = (data.get('role') or '').strip().lower()
    if role not in ('tl', 'sales'):
        return jsonify({'error': 'Rol inválido'}), 400
    conn = get_db()
    conn.execute('UPDATE users SET role=? WHERE id=? AND status="active"', (role, user_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'role': role})


@auth_bp.route('/me', methods=['GET'])
@login_required
def me():
    """Info del usuario actual para el frontend."""
    return jsonify({
        'id': current_user.id,
        'email': current_user.email,
        'username': current_user.username,
        'name': current_user.name,
        'role': current_user.role,
        'is_owner': current_user.is_owner,
        'is_tl': current_user.is_tl,             # True si tl O owner
        'is_only_tl': current_user.is_only_tl,   # True solo si tl puro
        'is_sales': current_user.is_sales,
        'can_manage_team': current_user.can_manage_team,
        'team_lead_id': current_user.team_lead_id,
        'password_changed': current_user.password_changed,
        'sig_title': current_user.sig_title,
        'sig_phone': current_user.sig_phone,
        'sig_photo_path': current_user.sig_photo_path,
        'smtp_user': current_user.smtp_user,
    })


# ═══════════════════════════════════════════════════════════════
# PERFIL — firma de email + credenciales SMTP por usuario
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/profile', methods=['GET'])
@login_required
def get_profile():
    """Devuelve el perfil completo del usuario (sin la password encriptada)."""
    conn = get_db()
    row = conn.execute('''
        SELECT id, email, username, name, role,
               sig_title, sig_phone, sig_photo_path,
               smtp_user, evolution_instance, whatsapp_number, apify_token,
               (smtp_pass_enc IS NOT NULL AND smtp_pass_enc != '') AS has_smtp_pass
        FROM users WHERE id = ?
    ''', (current_user.id,)).fetchone()
    conn.close()
    if not row:
        return jsonify({'error': 'no encontrado'}), 404
    d = dict(row)
    # Detectar si el perfil está completo para el wizard
    d['profile_complete'] = bool(d.get('sig_title') and d.get('sig_phone'))
    d['email_configured'] = bool(d.get('smtp_user') and d.get('has_smtp_pass'))
    d['has_apify_token'] = bool(d.get('apify_token'))
    # No devolvemos el token completo — solo si está seteado
    if d.get('apify_token'):
        d['apify_token_masked'] = d['apify_token'][:8] + '...' + d['apify_token'][-4:]
    d.pop('apify_token', None)
    return jsonify(d)


@auth_bp.route('/profile', methods=['POST'])
@login_required
def update_profile():
    """
    Actualiza firma + credenciales SMTP del usuario.
    Body: {sig_title, sig_phone, smtp_user, smtp_pass (plain — se encripta acá)}
    """
    from secure_storage import encrypt
    data = request.get_json() or {}

    sig_title = (data.get('sig_title') or '').strip()
    sig_phone = (data.get('sig_phone') or '').strip()
    smtp_user = (data.get('smtp_user') or '').strip().lower()
    smtp_pass_plain = data.get('smtp_pass') or ''  # opcional — solo si quiere cambiarla

    set_pairs = []
    params = []

    if 'sig_title' in data:
        set_pairs.append('sig_title=?')
        params.append(sig_title)
    if 'sig_phone' in data:
        set_pairs.append('sig_phone=?')
        params.append(sig_phone)
    if 'smtp_user' in data:
        # Validar email básico
        if smtp_user and '@' not in smtp_user:
            return jsonify({'error': 'smtp_user no es un email válido'}), 400
        set_pairs.append('smtp_user=?')
        params.append(smtp_user)
    if smtp_pass_plain:
        # Validar largo razonable (App Passwords de Gmail son 16 chars)
        cleaned = smtp_pass_plain.replace(' ', '').strip()
        if len(cleaned) < 8 or len(cleaned) > 64:
            return jsonify({'error': 'App Password debe tener 8-64 caracteres'}), 400
        encrypted = encrypt(cleaned)
        set_pairs.append('smtp_pass_enc=?')
        params.append(encrypted)
    if 'apify_token' in data:
        # Solo Owner/TL pueden setear su Apify token
        if current_user.role not in ('owner', 'tl'):
            return jsonify({'error': 'Solo Owner/TL pueden configurar Apify token'}), 403
        token = (data.get('apify_token') or '').strip()
        # Validar formato básico (Apify tokens son ~50 chars alfanuméricos)
        if token and (len(token) < 20 or ' ' in token):
            return jsonify({'error': 'Apify token inválido'}), 400
        set_pairs.append('apify_token=?')
        params.append(token if token else None)

    if not set_pairs:
        return jsonify({'error': 'No hay cambios para guardar'}), 400

    params.append(current_user.id)
    conn = get_db()
    conn.execute(f"UPDATE users SET {', '.join(set_pairs)} WHERE id=?", params)
    conn.commit()
    conn.close()
    return jsonify({'ok': True})


@auth_bp.route('/profile/signature-photo', methods=['POST'])
@login_required
def upload_signature_photo():
    """Sube foto de firma. Validamos: imagen JPEG/PNG, tamaño <2MB."""
    import os as _os
    if 'photo' not in request.files:
        return jsonify({'error': 'No se envió archivo'}), 400
    f = request.files['photo']
    if not f or not f.filename:
        return jsonify({'error': 'Archivo vacío'}), 400
    # Validar extensión
    fn = f.filename.lower()
    if not (fn.endswith('.jpg') or fn.endswith('.jpeg') or fn.endswith('.png')):
        return jsonify({'error': 'Solo JPG/JPEG/PNG'}), 400
    # Leer y validar tamaño (max 2MB)
    blob = f.read()
    if len(blob) > 2 * 1024 * 1024:
        return jsonify({'error': 'Foto muy grande (max 2MB)'}), 400
    if len(blob) < 100:
        return jsonify({'error': 'Foto inválida'}), 400
    # Validar que sea imagen real (anti-XSS via filename / fake extension)
    try:
        from PIL import Image
        from io import BytesIO
        img = Image.open(BytesIO(blob))
        img.verify()
    except Exception:
        return jsonify({'error': 'Archivo no es una imagen válida'}), 400

    # Guardar
    ext = 'jpg' if fn.endswith(('.jpg', '.jpeg')) else 'png'
    rel_path = f'email_assets/sigs/sig_user_{current_user.id}.{ext}'
    abs_path = _os.path.join(_os.path.dirname(_os.path.dirname(__file__)), 'static', rel_path)
    _os.makedirs(_os.path.dirname(abs_path), exist_ok=True)
    with open(abs_path, 'wb') as fp:
        fp.write(blob)

    # Guardar path en BD
    conn = get_db()
    conn.execute('UPDATE users SET sig_photo_path=? WHERE id=?',
                 (rel_path, current_user.id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'path': rel_path, 'url': f'/static/{rel_path}'})


@auth_bp.route('/profile/test-smtp', methods=['POST'])
@login_required
def test_smtp():
    """Prueba las credenciales SMTP del usuario enviando un email de prueba a sí mismo."""
    from secure_storage import decrypt
    import smtplib, ssl
    from email.mime.text import MIMEText

    conn = get_db()
    row = conn.execute(
        'SELECT smtp_user, smtp_pass_enc, name FROM users WHERE id=?',
        (current_user.id,)
    ).fetchone()
    conn.close()
    if not row or not row['smtp_user'] or not row['smtp_pass_enc']:
        return jsonify({'ok': False, 'error': 'Configurá tu email + App Password primero'}), 400

    pwd = decrypt(row['smtp_pass_enc'])
    if not pwd:
        return jsonify({'ok': False, 'error': 'No se pudo descifrar la password (clave de cifrado distinta?)'}), 500

    msg = MIMEText(
        f"Test exitoso de tu configuración SMTP en MP Prospecting.\n\n"
        f"Si recibiste este email, tu cuenta está lista para enviar campañas.\n\n"
        f"Saludos,\n{row['name']}",
        'plain', 'utf-8'
    )
    msg['Subject'] = '✓ Test MP Prospecting'
    msg['From'] = f"{row['name']} <{row['smtp_user']}>"
    msg['To'] = row['smtp_user']

    try:
        ctx = ssl.create_default_context()
        with smtplib.SMTP('smtp.gmail.com', 587, timeout=20) as s:
            s.ehlo(); s.starttls(context=ctx)
            s.login(row['smtp_user'], pwd)
            s.sendmail(row['smtp_user'], [row['smtp_user']], msg.as_string())
        return jsonify({'ok': True, 'mensaje': f"Email de prueba enviado a {row['smtp_user']}"})
    except smtplib.SMTPAuthenticationError as e:
        return jsonify({'ok': False, 'error': 'Auth falló — verificá tu App Password'}), 400
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)[:200]}), 500
