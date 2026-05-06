"""
Autenticación y autorización del dashboard.

Decisiones de seguridad:
- Passwords con bcrypt (no MD5/SHA, no plaintext)
- Sesiones via Flask-Login con cookies httponly + secure + samesite
- Rate limit por IP en /login y /register (anti fuerza bruta)
- Lockout por usuario tras 5 intentos fallidos (15 min)
- Email validado: debe ser @gmail.com (requerimiento del cliente)
- Auto-registro en estado 'pending' — TL aprueba y asigna rol
- Cambio de password forzado en primer login (campo password_changed)
- Filtros automáticos por user_id en queries de Sales (evita IDOR)
- CSRF token en forms POST via Flask-WTF
- Session-id se regenera al login (anti session fixation)
"""
import os
import re
import bcrypt
from datetime import datetime, timedelta
from functools import wraps
from flask import session, redirect, url_for, request, flash, abort, jsonify
from flask_login import LoginManager, UserMixin, login_user, logout_user, current_user, login_required

from database import get_db


# ── Constantes ─────────────────────────────────────────────────
MAX_FAILED_LOGINS = 5
LOCKOUT_MINUTES = 15
PASSWORD_MIN_LEN = 8
GMAIL_RE = re.compile(r'^[a-zA-Z0-9._%+\-]+@gmail\.com$', re.IGNORECASE)

# Email del Owner (creador). Se asigna rol 'owner' automáticamente al registrarse.
OWNER_EMAIL = os.getenv('OWNER_EMAIL', 'juansebastian.pinto.mp@gmail.com').strip().lower()


# ── Modelo User ─────────────────────────────────────────────────
class User(UserMixin):
    def __init__(self, row):
        self.id = row['id']
        self.email = row['email']
        self.username = row['username']
        self.role = row['role']
        self.name = row['name']
        self.status = row['status']
        self.password_changed = bool(row['password_changed'])
        self.evolution_instance = row['evolution_instance']
        self.whatsapp_number = row['whatsapp_number']
        self.fast_local_url = row['fast_local_url']
        self.smtp_user = row['smtp_user']
        # Equipo: a qué TL pertenece este usuario (NULL si es Owner o TL)
        try:
            self.team_lead_id = row['team_lead_id']
        except (KeyError, IndexError):
            self.team_lead_id = None
        # Firma personalizada
        try:
            self.sig_title = row['sig_title']
            self.sig_phone = row['sig_phone']
            self.sig_photo_path = row['sig_photo_path']
        except (KeyError, IndexError):
            self.sig_title = self.sig_phone = self.sig_photo_path = None

    @property
    def is_owner(self):
        return self.role == 'owner'

    @property
    def is_tl(self):
        # Owner también tiene capacidades de TL
        return self.role in ('tl', 'owner')

    @property
    def is_only_tl(self):
        """True solo si es TL (no owner). Útil para distinguir."""
        return self.role == 'tl'

    @property
    def is_sales(self):
        return self.role == 'sales'

    @property
    def can_manage_team(self):
        """Puede asignar leads, ver métricas de equipo."""
        return self.role in ('tl', 'owner')

    @property
    def can_send_with_own_signature(self):
        """Owner, TL y Sales — todos pueden tener su firma. Solo Sales asignados envían."""
        return self.role in ('owner', 'tl', 'sales')

    @property
    def is_active(self):
        # Flask-Login usa is_active para permitir el login.
        # Pending y disabled no pueden acceder.
        return self.status == 'active'


# ── Carga del usuario en la sesión ─────────────────────────────
def load_user(user_id):
    try:
        conn = get_db()
        row = conn.execute('SELECT * FROM users WHERE id = ?', (int(user_id),)).fetchone()
        conn.close()
        if row:
            return User(row)
    except Exception:
        pass
    return None


# ── Helpers de password ────────────────────────────────────────
def hash_password(plain: str) -> str:
    """Hash con bcrypt. cost=12 (balance velocidad/seguridad)."""
    return bcrypt.hashpw(plain.encode('utf-8'), bcrypt.gensalt(rounds=12)).decode('utf-8')


def verify_password(plain: str, hashed: str) -> bool:
    if not plain or not hashed:
        return False
    try:
        return bcrypt.checkpw(plain.encode('utf-8'), hashed.encode('utf-8'))
    except Exception:
        return False


def validate_password_strength(pwd: str) -> tuple[bool, str]:
    """Valida la robustez. Retorna (ok, mensaje_error)."""
    if len(pwd) < PASSWORD_MIN_LEN:
        return False, f'La contraseña debe tener al menos {PASSWORD_MIN_LEN} caracteres'
    if not re.search(r'[A-Za-z]', pwd):
        return False, 'La contraseña debe incluir al menos una letra'
    if not re.search(r'\d', pwd):
        return False, 'La contraseña debe incluir al menos un número'
    return True, ''


def validate_gmail(email: str) -> bool:
    return bool(GMAIL_RE.match((email or '').strip()))


# ── Lockout helpers ────────────────────────────────────────────
def is_user_locked(row) -> bool:
    locked_until = row['locked_until']
    if not locked_until:
        return False
    try:
        until = datetime.fromisoformat(locked_until)
        return datetime.now() < until
    except Exception:
        return False


def register_failed_login(user_id: int):
    conn = get_db()
    row = conn.execute('SELECT failed_logins FROM users WHERE id=?', (user_id,)).fetchone()
    if row:
        new_count = (row['failed_logins'] or 0) + 1
        if new_count >= MAX_FAILED_LOGINS:
            until = (datetime.now() + timedelta(minutes=LOCKOUT_MINUTES)).isoformat(timespec='seconds')
            conn.execute('UPDATE users SET failed_logins=?, locked_until=? WHERE id=?',
                         (new_count, until, user_id))
        else:
            conn.execute('UPDATE users SET failed_logins=? WHERE id=?', (new_count, user_id))
        conn.commit()
    conn.close()


def clear_failed_logins(user_id: int):
    conn = get_db()
    conn.execute('UPDATE users SET failed_logins=0, locked_until=NULL, last_login=? WHERE id=?',
                 (datetime.now().isoformat(timespec='seconds'), user_id))
    conn.commit()
    conn.close()


# ── Decoradores de rol ─────────────────────────────────────────
def requires_role(*allowed_roles):
    """
    Decorador para endpoints que requieren rol específico.
    Uso:  @requires_role('tl')  o  @requires_role('tl', 'sales')

    Owner SIEMPRE pasa (super-admin). Esto evita tener que listar 'owner'
    en cada decorador.
    """
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.status != 'active':
                return jsonify({'error': 'Cuenta no activa'}), 403
            # Owner = super-admin, acceso a todo
            if current_user.role == 'owner':
                return fn(*args, **kwargs)
            if current_user.role not in allowed_roles:
                # 403 con mensaje genérico — no revelar info sobre roles
                return jsonify({'error': 'No tienes permiso para esta acción'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


def requires_tl(fn):
    """TL o Owner."""
    return requires_role('tl')(fn)


def requires_owner(fn):
    """Solo Owner — acciones súper-admin (cambiar config global, etc.)."""
    def decorator(fn):
        @wraps(fn)
        @login_required
        def wrapper(*args, **kwargs):
            if current_user.role != 'owner' or current_user.status != 'active':
                return jsonify({'error': 'Solo el owner del sistema puede hacer esto'}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator(fn)


def requires_sales(fn):
    return requires_role('sales')(fn)


def requires_authenticated(fn):
    """Sólo requiere estar autenticado (cualquier rol activo)."""
    return requires_role('tl', 'sales')(fn)


# ── Helper para filtrar leads por rol ─────────────────────────
def get_user_leads_filter(user, alias='l'):
    """
    Devuelve (sql_where, params) para filtrar la tabla leads según el rol del usuario.

    - Owner: ve todos los leads (incluso sin asignar) → '1=1'
    - TL:    ve leads asignados a su equipo (sus Sales + él mismo)
    - Sales: solo leads asignados a él (assigned_to = user.id)

    Esto es CRÍTICO para evitar IDOR — si un Sales pide /api/leads, el SQL
    siempre incluye su filtro y nunca puede ver leads de otros usuarios.
    """
    if not user or not user.status == 'active':
        return '0=1', []
    if user.role == 'owner':
        return '1=1', []
    if user.role == 'tl':
        # Su equipo = él mismo + sus Sales (donde team_lead_id = su id)
        return (
            f'({alias}.assigned_to = ? OR {alias}.assigned_to IN '
            f'(SELECT id FROM users WHERE team_lead_id = ? AND status="active"))',
            [user.id, user.id]
        )
    if user.role == 'sales':
        return f'{alias}.assigned_to = ?', [user.id]
    return '0=1', []


def get_team_user_ids(user, conn):
    """
    Devuelve los IDs de usuarios visibles para este usuario.
    Útil para queries de mensajes, prospects, etc. que se filtran por usuario.
    """
    if user.role == 'owner':
        rows = conn.execute('SELECT id FROM users WHERE status="active"').fetchall()
        return [r['id'] for r in rows]
    if user.role == 'tl':
        rows = conn.execute(
            'SELECT id FROM users WHERE status="active" AND (id = ? OR team_lead_id = ?)',
            (user.id, user.id)
        ).fetchall()
        return [r['id'] for r in rows]
    if user.role == 'sales':
        return [user.id]
    return []


# ── Init Flask-Login ────────────────────────────────────────────
def init_login_manager(app):
    login_manager = LoginManager()
    login_manager.login_view = 'auth.login'
    login_manager.session_protection = 'strong'  # invalida sesión si cambia IP/UserAgent
    login_manager.user_loader(load_user)
    login_manager.init_app(app)

    # Cookies seguras
    app.config['SESSION_COOKIE_HTTPONLY'] = True
    app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
    # SECURE solo en HTTPS — Railway sirve via HTTPS
    app.config['SESSION_COOKIE_SECURE'] = True
    app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(hours=8)
    app.config['REMEMBER_COOKIE_HTTPONLY'] = True
    app.config['REMEMBER_COOKIE_SECURE'] = True

    return login_manager
