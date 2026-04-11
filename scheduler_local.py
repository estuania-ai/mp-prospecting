"""
Scheduler local - reemplaza Task Scheduler
Deja esta ventana abierta todo el dia
Envia automaticamente a los horarios programados L-V
"""
import time
import subprocess
import sys
import os
import logging
from datetime import datetime

os.chdir(os.path.dirname(os.path.abspath(__file__)) if '__file__' in dir() else os.getcwd())
sys.path.insert(0, os.getcwd())

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler('logs/scheduler_local.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Horarios L-V: (hora, minuto, batch_numero, descripcion)
HORARIOS_PROSPECCION = [
    ('09', '30', '1', '15 mensajes'),
    ('15', '00', '2', '10 mensajes'),
    ('17', '30', '3', '15 mensajes'),
]

# Fidelizacion todos los dias a las 11:00
HORA_FIDELIZACION = ('11', '00')
# Seguimiento todos los dias a las 12:00
HORA_SEGUIMIENTO = ('12', '00')

ejecutados_hoy = set()

print("=" * 50)
print("  MP Prospecting - Scheduler Local")
print("=" * 50)
print("Prospeccion L-V:")
for h, m, b, desc in HORARIOS_PROSPECCION:
    print(f"  {h}:{m} -> Lote {b} ({desc})")
print(f"Fidelizacion sellers todos los dias:")
print(f"  {HORA_FIDELIZACION[0]}:{HORA_FIDELIZACION[1]} -> Mensajes por etapa (7,14,15,30,35 dias)")
print(f"Seguimiento leads sin respuesta todos los dias:")
print(f"  {HORA_SEGUIMIENTO[0]}:{HORA_SEGUIMIENTO[1]} -> 24h y 72h sin respuesta")
print()
print("Deja esta ventana abierta. Ctrl+C para detener.")
print("=" * 50)
print()

while True:
    now = datetime.now()
    dia_semana = now.weekday()  # 0=Lunes, 6=Domingo
    hora = now.strftime('%H')
    minuto = now.strftime('%M')
    fecha = str(now.date())

    # ── Seguimiento diario 12:00 ────────────────────────
    seg_clave = f"{fecha}_seguimiento"
    if hora == HORA_SEGUIMIENTO[0] and minuto == HORA_SEGUIMIENTO[1] and seg_clave not in ejecutados_hoy:
        logger.info("Iniciando seguimiento de leads sin respuesta...")
        ejecutados_hoy.add(seg_clave)
        try:
            from jobs.send_seguimiento import run_seguimiento
            run_seguimiento()
            logger.info("Seguimiento completado")
        except Exception as e:
            logger.error(f"Error en seguimiento: {e}")

    # ── Fidelizacion diaria 11:00 ───────────────────────
    fid_clave = f"{fecha}_fidelizacion"
    if hora == HORA_FIDELIZACION[0] and minuto == HORA_FIDELIZACION[1] and fid_clave not in ejecutados_hoy:
        logger.info("Iniciando fidelizacion de sellers...")
        ejecutados_hoy.add(fid_clave)
        try:
            from jobs.send_fidelizacion import run_fidelizacion
            run_fidelizacion()
            logger.info("Fidelizacion completada")
        except Exception as e:
            logger.error(f"Error en fidelizacion: {e}")

    # ── Prospeccion L-V ──────────────────────────────────
    if dia_semana <= 4:
        for h, m, batch, desc in HORARIOS_PROSPECCION:
            clave = f"{fecha}_{h}_{m}"
            if hora == h and minuto == m and clave not in ejecutados_hoy:
                logger.info(f"Iniciando lote {batch} ({desc})...")
                ejecutados_hoy.add(clave)
                try:
                    subprocess.run([sys.executable, 'run_batch.py', batch])
                    logger.info(f"Lote {batch} completado")
                except Exception as e:
                    logger.error(f"Error en lote {batch}: {e}")

    # ── Countdown cada 5 minutos ────────────────────────
    if now.minute % 5 == 0 and now.second < 10:
        proximos = []
        if dia_semana <= 4:
            for h, m, b, desc in HORARIOS_PROSPECCION:
                target = now.replace(hour=int(h), minute=int(m), second=0)
                if target > now:
                    diff = int((target - now).total_seconds() / 60)
                    proximos.append(f"Lote {b} en {diff} min")

        fid_target = now.replace(hour=int(HORA_FIDELIZACION[0]), minute=int(HORA_FIDELIZACION[1]), second=0)
        if fid_target > now:
            diff_f = int((fid_target - now).total_seconds() / 60)
            proximos.append(f"Fidelizacion en {diff_f} min")

        if proximos:
            logger.info("Proximos: " + " | ".join(proximos))

    time.sleep(10)
