"""
Script de envio por lotes - llamado por Task Scheduler de Windows
Uso: python run_batch.py 1  (lote 1 = 09:30, 15 mensajes)
     python run_batch.py 2  (lote 2 = 15:00, 10 mensajes)
     python run_batch.py 3  (lote 3 = 17:30, 15 mensajes)
"""
import sys
import os
import logging

# Asegurar que el directorio del script sea el directorio de trabajo
os.chdir(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/batch_runs.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

BATCH_CONFIG = {
    '1': {'limit': 15, 'name': '09:30'},
    '2': {'limit': 10, 'name': '15:00'},
    '3': {'limit': 15, 'name': '17:30'},
}

if __name__ == '__main__':
    batch_num = sys.argv[1] if len(sys.argv) > 1 else '1'
    config = BATCH_CONFIG.get(batch_num, BATCH_CONFIG['1'])

    logger.info(f"=== Iniciando lote {batch_num} ({config['name']}) - {config['limit']} mensajes ===")

    try:
        from database import init_db
        init_db()

        from jobs.send_prospecting import run_prospecting_batch
        run_prospecting_batch(config['limit'], config['name'])

        logger.info(f"=== Lote {batch_num} completado ===")

    except Exception as e:
        logger.error(f"Error en lote {batch_num}: {e}", exc_info=True)
        sys.exit(1)
