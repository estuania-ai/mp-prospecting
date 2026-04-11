"""
MercadoPago POS Prospecting System
Backend Flask - 3 lotes diarios L-V
"""

from flask import Flask, render_template, jsonify
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger
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
app.secret_key = 'mp_prospecting_2025_secret'

app.register_blueprint(leads_bp,      url_prefix='/api/leads')
app.register_blueprint(prospects_bp, url_prefix='/api/prospects')
app.register_blueprint(campaigns_bp,  url_prefix='/api/campaigns')
app.register_blueprint(sellers_bp,    url_prefix='/api/sellers')
app.register_blueprint(dashboard_bp,  url_prefix='/api/dashboard')
app.register_blueprint(scraping_bp,   url_prefix='/api/scraping')
app.register_blueprint(intel_bp,      url_prefix='/api/intel')
app.register_blueprint(manual_bp,     url_prefix='/api/manual')


@app.route('/')
def index():
    return render_template('dashboard.html')


# ── SCHEDULER ─────────────────────────────────────────────────
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


# 09:30 AM - 15 mensajes
scheduler.add_job(job_batch1, CronTrigger(day_of_week='mon-fri', hour=9,  minute=30),
                  id='batch_0930', replace_existing=True)
# 15:00 PM - 10 mensajes
scheduler.add_job(job_batch2, CronTrigger(day_of_week='mon-fri', hour=15, minute=0),
                  id='batch_1500', replace_existing=True)
# 17:30 PM - 15 mensajes
scheduler.add_job(job_batch3, CronTrigger(day_of_week='mon-fri', hour=17, minute=30),
                  id='batch_1730', replace_existing=True)
# Fidelizacion lunes 11:00
scheduler.add_job(job_fidelizacion, CronTrigger(day_of_week='mon', hour=11, minute=0),
                  id='fidelizacion_weekly', replace_existing=True)

scheduler.start()
atexit.register(lambda: scheduler.shutdown())


@app.route('/api/scheduler/status')
def scheduler_status():
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            'id': job.id,
            'next_run': str(job.next_run_time),
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
            'prospecting_daily':   job_batch1,  # compatibilidad
        }
        fn = map_jobs.get(job_id)
        if fn:
            fn()
        return jsonify({'ok': True, 'message': f'Job {job_id} ejecutado'})
    except Exception as e:
        return jsonify({'ok': False, 'error': str(e)}), 500



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


if __name__ == '__main__':
    init_db()
    logger.info("MercadoPago Prospecting System iniciado")
    app.run(debug=True, port=5000, use_reloader=False)
