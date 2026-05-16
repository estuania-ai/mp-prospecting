"""
MercadoPago POS Prospecting System
Backend Flask - 3 lotes diarios L-V
"""

from dotenv import load_dotenv
load_dotenv()

from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
from apscheduler.triggers.interval import IntervalTrigger
import atexit
import logging
from database import init_db
from routes.leads import leads_bp
from routes.prospects import prospects_bp
from routes.campaigns import campaigns_bp
from routes.sellers import sellers_bp
from routes.dashboard import dashboard_bp
from routes.scraping import scraping_bp
from routes.prospecting_intel import intel_bp
from routes.manual_send import manual_bp
from routes.fast_registro import fast_bp
from routes.email_tool import email_bp
from routes.whatsapp_routes import bp as whatsapp_bp
from routes.twilio_routes import bp as twilio_bp
from routes.auth_routes import auth_bp
from auth import init_login_manager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/app.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# SECRET_KEY desde env (en producción) — el default solo para dev local
import os
app.secret_key = os.getenv('FLASK_SECRET_KEY', 'mp_prospecting_2025_secret_DEV_ONLY_change_in_prod')

# IMPORTANTE: init_db debe ejecutarse al cargar el modulo (no solo en __main__)
# porque gunicorn importa app.py sin ejecutar el bloque __main__.
try:
    init_db()
    logger.info("init_db() ejecutado correctamente")
except Exception as _e:
    logger.error(f"init_db() falló: {_e}", exc_info=True)

# Inicializar Flask-Login + cookies seguras
init_login_manager(app)

app.register_blueprint(auth_bp)  # /auth/login, /auth/register, etc.
app.register_blueprint(leads_bp,      url_prefix='/api/leads')
app.register_blueprint(prospects_bp, url_prefix='/api/prospects')
app.register_blueprint(campaigns_bp,  url_prefix='/api/campaigns')
app.register_blueprint(sellers_bp,    url_prefix='/api/sellers')
app.register_blueprint(dashboard_bp,  url_prefix='/api/dashboard')
app.register_blueprint(scraping_bp,   url_prefix='/api/scraping')
app.register_blueprint(intel_bp,      url_prefix='/api/intel')
app.register_blueprint(manual_bp,     url_prefix='/api/manual')
app.register_blueprint(fast_bp,       url_prefix='/api/leads')
app.register_blueprint(email_bp,      url_prefix='/api/email-tool')
app.register_blueprint(whatsapp_bp)
app.register_blueprint(twilio_bp)   # /api/twilio/* · activo solo si WA_BACKEND=twilio


# ── Middleware: forzar login en todas las rutas no-publicas ──
from flask import redirect, url_for, request
from flask_login import current_user

PUBLIC_PATHS = {'/auth/login', '/auth/register', '/health', '/favicon.ico'}
PUBLIC_PREFIXES = ('/static/',)

@app.before_request
def require_login():
    p = request.path
    if p in PUBLIC_PATHS or p.startswith(PUBLIC_PREFIXES):
        return None
    if current_user.is_authenticated:
        # Forzar cambio de password si nunca lo hizo
        if not current_user.password_changed and p != '/auth/change-password' and not p.startswith('/auth/'):
            return redirect(url_for('auth.change_password'))
        return None
    # No autenticado — devolver 401 si es API, redirigir si es UI
    if p.startswith('/api/'):
        from flask import jsonify
        return jsonify({'error': 'Autenticación requerida'}), 401
    return redirect(url_for('auth.login'))


@app.route('/')
def index():
    # Servir el dashboard que usamos en producción (test14)
    return render_template('dashboard_test14.html')


@app.route('/health')
def health():
    return {'ok': True}


# Endpoint público para cabeceras de seguridad básicas
@app.after_request
def security_headers(resp):
    resp.headers.setdefault('X-Content-Type-Options', 'nosniff')
    resp.headers.setdefault('X-Frame-Options', 'SAMEORIGIN')
    resp.headers.setdefault('Referrer-Policy', 'same-origin')
    return resp


# â”€â”€ SCHEDULER â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€â”€
scheduler = BackgroundScheduler(timezone='America/Santiago')


def job_batch1():
    """Lote 1: 15 mensajes a las 09:30 L-V"""
    from jobs.send_prospecting import run_batch1
    run_batch1()

def job_batch2():
    """Lote 2: 10 mensajes a las 15:00 L-V"""
    from jobs.send_prospecting import run_batch2
    run_batch2()

def job_batch3():
    """Lote 3: 15 mensajes a las 17:30 L-V"""
    from jobs.send_prospecting import run_batch3
    run_batch3()

def job_fidelizacion():
    """Fidelizacion sellers - Lunes 11:00"""
    from jobs.send_fidelizacion import run_fidelizacion
    run_fidelizacion()

def job_email_lote1():
    """09:00 L-V — Lote Mañana: 40 emails (Regla 1-2-4-6)"""
    from jobs.email_automation import run_lote_manana_in_thread
    run_lote_manana_in_thread()

def job_email_lote2():
    """12:00 L-V — Lote Mediodía: 35 emails (Regla 1-2-4-6)"""
    from jobs.email_automation import run_lote_mediodia_in_thread
    run_lote_mediodia_in_thread()

def job_email_lote3():
    """16:00 L-V — Lote Tarde: 25 emails (Regla 1-2-4-6)"""
    from jobs.email_automation import run_lote_tarde_in_thread
    run_lote_tarde_in_thread()

def job_email_followup():
    """Follow-up automático 48h/96h — cada 2 horas"""
    from jobs.email_automation import run_followup_in_thread
    run_followup_in_thread()

def job_inbox_monitor():
    """Monitor de bandeja: detecta respuestas y rebotes via Gmail API — cada 30 min.
    Corre en un thread con timeout de 4 minutos para evitar que un cuelgue de
    Chrome/Playwright bloquee el proceso Flask."""
    import threading
    from jobs.inbox_monitor import check_inbox_in_thread

    t = threading.Thread(target=check_inbox_in_thread, daemon=True, name='inbox_monitor')
    t.start()
    t.join(timeout=240)  # máximo 4 minutos; si sigue corriendo lo abandona (daemon)
    if t.is_alive():
        logger.warning("[inbox_monitor] Timeout de 4 min — thread abandonado. Revisar Playwright/Chrome.")

def job_auto_scraping():
    """08:00 diario — Rellena pool hasta 1000 leads no_enviado via Brave/Google/Outscraper.
    Si pool >= 1000 no hace nada. Timeout 25 min."""
    import threading
    from jobs.email_automation import run_intel_scraping

    t = threading.Thread(target=run_intel_scraping, daemon=True, name='auto_scraping')
    t.start()
    t.join(timeout=1500)  # máximo 25 minutos
    if t.is_alive():
        logger.warning("[auto_scraping] Timeout de 25 min — thread abandonado.")

def job_wa_followup():
    """10:00 diario — Follow-up WhatsApp para emails sin respuesta hace +N días."""
    import threading
    from jobs.wa_followup import run_wa_followup

    t = threading.Thread(target=run_wa_followup, daemon=True, name='wa_followup')
    t.start()
    t.join(timeout=3600)  # máximo 1 hora
    if t.is_alive():
        logger.warning("[wa_followup] Timeout de 1h — thread abandonado.")

def job_wa_seguimiento():
    """Cada 2h L-V — Seguimiento WA automático para leads WA en estado 'enviado' 24h/72h.
    Respeta ventanas de prospección (09:30, 15:00, 17:30 ±15min)."""
    import threading
    from jobs.wa_seguimiento import run_wa_seguimiento

    t = threading.Thread(target=run_wa_seguimiento, daemon=True, name='wa_seguimiento')
    t.start()
    t.join(timeout=1800)  # máximo 30 minutos
    if t.is_alive():
        logger.warning("[wa_seguimiento] Timeout de 30min — thread abandonado.")


# ── Parámetros comunes ────────────────────────────────────────────────────────
# misfire_grace_time=3600 → si el proceso estuvo caído, ejecuta el job siempre
#   que haya pasado menos de 1 hora desde la hora programada (evita el skip por
#   default de APScheduler que tiene gracia de ~1 segundo).
# coalesce=True          → si se perdieron N disparos consecutivos, ejecuta 1 solo.
# max_instances=1        → nunca corre dos copias simultáneas del mismo job.
_JOB_OPTS  = dict(max_instances=1, coalesce=True, misfire_grace_time=3600)
_INTVL_OPTS = dict(max_instances=1, coalesce=True, misfire_grace_time=600)  # intervalos cortos

# 09:30 AM - 15 mensajes
scheduler.add_job(job_batch1, CronTrigger(day_of_week='mon-fri', hour=9,  minute=30),
                  id='batch_0930', replace_existing=True, **_JOB_OPTS)
# 15:00 PM - 10 mensajes
scheduler.add_job(job_batch2, CronTrigger(day_of_week='mon-fri', hour=15, minute=0),
                  id='batch_1500', replace_existing=True, **_JOB_OPTS)
# 17:30 PM - 15 mensajes
scheduler.add_job(job_batch3, CronTrigger(day_of_week='mon-fri', hour=17, minute=30),
                  id='batch_1730', replace_existing=True, **_JOB_OPTS)
# Fidelizacion lunes 11:00
scheduler.add_job(job_fidelizacion, CronTrigger(day_of_week='mon', hour=11, minute=0),
                  id='fidelizacion_weekly', replace_existing=True, **_JOB_OPTS)
# Email — 3 lotes L-V (Reglas 1-2-4-6)
scheduler.add_job(job_email_lote1, CronTrigger(day_of_week='mon-fri', hour=9,  minute=0),
                  id='email_lote1', replace_existing=True, **_JOB_OPTS)
scheduler.add_job(job_email_lote2, CronTrigger(day_of_week='mon-fri', hour=12, minute=0),
                  id='email_lote2', replace_existing=True, **_JOB_OPTS)
scheduler.add_job(job_email_lote3, CronTrigger(day_of_week='mon-fri', hour=16, minute=0),
                  id='email_lote3', replace_existing=True, **_JOB_OPTS)
# Email follow-up cada 2 horas — detecta y envía seguimientos 48h y 96h en ventana ajustada
scheduler.add_job(job_email_followup, IntervalTrigger(hours=2),
                  id='email_followup', replace_existing=True, **_INTVL_OPTS)
# Monitor de bandeja — cada 30 minutos detecta respuestas y rebotes
scheduler.add_job(job_inbox_monitor, IntervalTrigger(minutes=30),
                  id='inbox_monitor', replace_existing=True, **_INTVL_OPTS)
# Scraping automático todos los días 08:00 — busca nuevos contactos de email según Inteligencia
scheduler.add_job(job_auto_scraping, CronTrigger(hour=8, minute=0),
                  id='auto_scraping', replace_existing=True, **_JOB_OPTS)
# WhatsApp follow-up 10:00 diario — envía WA a emails sin respuesta hace +N días
scheduler.add_job(job_wa_followup, CronTrigger(hour=10, minute=0),
                  id='wa_followup', replace_existing=True, **_JOB_OPTS)
# Seguimiento WA automático cada 2h L-V — 24h y 72h para leads en estado 'enviado'
# (la función internamente verifica ventanas de prospección antes de enviar)
scheduler.add_job(job_wa_seguimiento, IntervalTrigger(hours=2),
                  id='wa_seguimiento', replace_existing=True, **_INTVL_OPTS)

scheduler.start()
atexit.register(lambda: scheduler.shutdown())


@app.route('/api/scheduler/status')
def scheduler_status():
    jobs = []
    for job in scheduler.get_jobs():
        nrt = job.next_run_time
        # Devolver epoch ms (entero) — completamente libre de ambigüedades de timezone.
        # JS: new Date(ts_ms) siempre crea el momento UTC correcto.
        if nrt:
            try:
                next_run_ms = int(nrt.timestamp() * 1000)
            except Exception:
                next_run_ms = None
        else:
            next_run_ms = None
        jobs.append({
            'id': job.id,
            'next_run': next_run_ms,   # epoch ms, e.g. 1745836200000
            'trigger': str(job.trigger)
        })
    return jsonify({'running': scheduler.running, 'jobs': jobs})


@app.route('/api/scheduler/trigger/<job_id>', methods=['POST'])
def trigger_job(job_id):
    """Disparo manual para pruebas desde dashboard"""
    try:
        map_jobs = {
            'batch_0930':          job_batch1,
            'batch_1500':          job_batch2,
            'batch_1730':          job_batch3,
            'fidelizacion_weekly': job_fidelizacion,
            'email_lote1':         job_email_lote1,
            'email_lote2':         job_email_lote2,
            'email_lote3':         job_email_lote3,
            'email_daily':         job_email_lote1,   # alias legacy
            'email_followup':      job_email_followup,
            'auto_scraping':       job_auto_scraping,
            'wa_followup':         job_wa_followup,
            'wa_seguimiento':      job_wa_seguimiento,
        }
        fn = map_jobs.get(job_id)
        if fn:
            fn()
        return jsonify({'ok': True, 'message': f'Job {job_id} ejecutado'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/api/cleanup/landline-numbers', methods=['POST'])
def cleanup_landline_numbers():
    """Marca todos los números fijos (562XXXXXXX) como teléfono no existe"""
    try:
        conn = get_db()

        # Encontrar todos los leads con números fijos
        landlines = conn.execute('''
            SELECT l.id, l.name, l.phone FROM leads l
            WHERE (l.phone LIKE '562%' OR l.phone LIKE '+562%')
              AND l.id NOT IN (
                SELECT DISTINCT lead_id FROM lead_status
                WHERE status = 'telefono_no_existe'
              )
        ''').fetchall()

        if not landlines:
            conn.close()
            return jsonify({'ok': True, 'message': 'No hay números fijos para procesar', 'cleaned': 0})

        landlines = [dict(r) for r in landlines]

        # Marcar como teléfono no existe
        for lead in landlines:
            conn.execute('''
                INSERT INTO lead_status (lead_id, status, updated_at, notes)
                VALUES (?, 'telefono_no_existe', datetime('now','localtime'), 'Número fijo 562 - no soporta WhatsApp')
                ON CONFLICT(lead_id) DO UPDATE SET
                    status = 'telefono_no_existe',
                    notes = 'Número fijo 562 - no soporta WhatsApp',
                    updated_at = datetime('now','localtime')
            ''', (lead['id'],))

        conn.commit()
        conn.close()

        return jsonify({
            'ok': True,
            'message': f'{len(landlines)} números fijos marcados como "Sin teléfono"',
            'cleaned': len(landlines),
            'leads': [{'id': l['id'], 'name': l['name'], 'phone': l['phone']} for l in landlines]
        })
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500


@app.route('/email-tool')
def email_tool():
    return render_template('email_tool.html')


@app.route('/emailing')
def emailing_dashboard():
    from flask import make_response
    resp = make_response(render_template('email_dashboard.html'))
    resp.headers['Cache-Control'] = 'no-store, no-cache, must-revalidate, max-age=0'
    resp.headers['Pragma'] = 'no-cache'
    return resp


@app.route('/test')
def index_test():
    return render_template('dashboard_test.html')

@app.route('/test2')
def index_test2():
    return render_template('dashboard_test2.html')

@app.route('/test3')
def index_test3():
    return render_template('dashboard_test3.html')

@app.route('/test4')
def index_test4():
    return render_template('dashboard_test4.html')

@app.route('/test5')
def index_test5():
    return render_template('dashboard_test5.html')

@app.route('/test6')
def index_test6():
    return render_template('dashboard_test6.html')

@app.route('/test7')
def index_test7():
    return render_template('dashboard_test7.html')

@app.route('/test8')
def index_test8():
    return render_template('dashboard_test8.html')
@app.route('/test9')
def index_test9():
    return render_template('dashboard_test9.html')
@app.route('/test10')
def index_test10():
    return render_template('dashboard_test10.html')
@app.route('/test11')
def index_test11():
    return render_template('dashboard_test11.html')
@app.route('/test12')
def index_test12():
    return render_template('dashboard_test12.html')
@app.route('/test13')
def index_test13():
    return render_template('dashboard_test13.html')


@app.route('/test14')
def index_test14():
    return render_template('dashboard_test14.html')

def _migrate_pendiente():
    """
    Migración única: convierte campaign_status='pendiente' a 'no_enviado'
    en todos los contactos sin fecha_envio (nunca se les envió nada).
    Elimina el estado 'pendiente' del sistema.
    """
    try:
        from database import get_db
        conn = get_db()
        cur = conn.execute(
            "UPDATE et_contacts SET campaign_status='no_enviado' "
            "WHERE campaign_status='pendiente' "
            "AND (fecha_envio IS NULL OR fecha_envio = '')"
        )
        if cur.rowcount:
            logger.info(f"[Migración] {cur.rowcount} contactos 'pendiente' → 'no_enviado'")
        # Los pendiente CON fecha_envio realmente fueron enviados → marcar como enviado
        cur2 = conn.execute(
            "UPDATE et_contacts SET campaign_status='enviado' "
            "WHERE campaign_status='pendiente' "
            "AND fecha_envio IS NOT NULL AND fecha_envio != ''"
        )
        if cur2.rowcount:
            logger.info(f"[Migración] {cur2.rowcount} contactos 'pendiente' con envío → 'enviado'")
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f"[Migración] Error: {e}")


# ── Endpoint temporal para restaurar base de datos ──────────────────
import os as _os_tmp
_UPLOAD_SECRET = _os_tmp.environ.get('DB_UPLOAD_SECRET', '')

@app.route('/admin/restore-db', methods=['POST'])
def restore_db():
    from flask import request
    if not _UPLOAD_SECRET or request.headers.get('X-Secret') != _UPLOAD_SECRET:
        return jsonify({'error': 'unauthorized'}), 401
    if 'file' not in request.files:
        return jsonify({'error': 'no file'}), 400
    f = request.files['file']
    dest = _os_tmp.path.join(_os_tmp.path.dirname(__file__), 'data', 'prospecting.db')
    _os_tmp.makedirs(_os_tmp.path.dirname(dest), exist_ok=True)
    f.save(dest)
    return jsonify({'ok': True, 'size': _os_tmp.path.getsize(dest)})
# ────────────────────────────────────────────────────────────────────

if __name__ == '__main__':
    import os as _os
    init_db()
    _migrate_pendiente()
    logger.info("MercadoPago Prospecting System iniciado")
    # Railway asigna el puerto en la variable PORT; localmente usa 5000
    _port = int(_os.environ.get('PORT', 5000))
    _debug = _os.environ.get('RAILWAY_ENVIRONMENT') is None  # False en producción
    app.run(host='0.0.0.0', debug=_debug, port=_port, use_reloader=False)



