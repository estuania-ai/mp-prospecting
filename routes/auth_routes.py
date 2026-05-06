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
    requires_tl, MAX_FAILED_LOGINS, LOCKOUT_MINUTES
)

auth_bp = Blueprint('auth', __name__, url_prefix='/auth')


# ═══════════════════════════════════════════════════════════════
# LOGIN
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

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

        return redirect(url_for('dashboard'))

    return render_template('auth/login.html')


# ═══════════════════════════════════════════════════════════════
# REGISTRO (queda pending, TL aprueba)
# ═══════════════════════════════════════════════════════════════
@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

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

        # Si es el primer usuario del sistema → bootstrap como TL aprobado
        first_user = conn.execute('SELECT COUNT(*) AS c FROM users').fetchone()['c'] == 0

        conn.execute('''
            INSERT INTO users (email, username, password_hash, name, role, status, password_changed)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            email, username, hash_password(password), name,
            'tl' if first_user else None,
            'active' if first_user else 'pending',
            1 if first_user else 0
        ))
        conn.commit()
        conn.close()

        if first_user:
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
        return redirect(url_for('dashboard'))

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
    """Aprueba un usuario pendiente y le asigna rol."""
    data = request.get_json() or {}
    role = (data.get('role') or '').strip().lower()
    if role not in ('tl', 'sales'):
        return jsonify({'error': 'Rol inválido'}), 400

    conn = get_db()
    row = conn.execute('SELECT id, status FROM users WHERE id=?', (user_id,)).fetchone()
    if not row:
        conn.close()
        return jsonify({'error': 'Usuario no encontrado'}), 404
    if row['status'] != 'pending':
        conn.close()
        return jsonify({'error': f'Usuario ya está en estado: {row["status"]}'}), 400

    conn.execute('UPDATE users SET role=?, status="active" WHERE id=?', (role, user_id))
    conn.commit()
    conn.close()
    return jsonify({'ok': True, 'role': role})


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
        'is_tl': current_user.is_tl,
        'is_sales': current_user.is_sales,
        'password_changed': current_user.password_changed,
    })
