"""
Watchdog Fast: garantiza que servidor local + tunel cloudflared esten corriendo.
Se ejecuta cada 1 minuto via Task Scheduler con pythonw.exe (sin ventana).

Si alguno cae, lo relanza oculto.
"""
import os
import subprocess
import sys
import time
import urllib.request
from datetime import datetime
from pathlib import Path

PROJECT_DIR  = Path(r"C:\Users\juanspinto\mp_prospecting")
CLOUDFLARED  = Path(r"C:\Users\juanspinto\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe")
TOKEN        = "mp-fast-2026-secret"
LOG_FILE     = PROJECT_DIR / "logs" / "fast_watchdog.log"

# CREATE_NO_WINDOW flag de Windows (0x08000000) — lanza procesos sin ventana
CREATE_NO_WINDOW = 0x08000000


def log(msg: str):
    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    with open(LOG_FILE, "a", encoding="utf-8") as f:
        f.write(f"{datetime.now().isoformat(timespec='seconds')} - {msg}\n")


def is_flask_alive() -> bool:
    try:
        with urllib.request.urlopen("http://127.0.0.1:5050/health", timeout=3) as r:
            return r.status == 200
    except Exception:
        return False


def is_cloudflared_running() -> bool:
    try:
        out = subprocess.check_output(
            ["tasklist", "/FI", "IMAGENAME eq cloudflared.exe", "/NH"],
            creationflags=CREATE_NO_WINDOW,
            text=True,
            timeout=10,
        )
        return "cloudflared.exe" in out.lower()
    except Exception:
        return False


def kill_dead_pythonw():
    """Mata pythonw que tengan fast_local_server colgado."""
    try:
        subprocess.run(
            ["taskkill", "/F", "/FI", "WINDOWTITLE eq fast_local_server*", "/T"],
            creationflags=CREATE_NO_WINDOW,
            timeout=5,
            capture_output=True,
        )
    except Exception:
        pass


def start_flask():
    env = os.environ.copy()
    env["FAST_LOCAL_TOKEN"] = TOKEN
    env["FAST_HEADLESS"] = "false"
    pythonw = sys.executable.replace("python.exe", "pythonw.exe")
    if not Path(pythonw).exists():
        pythonw = "pythonw.exe"
    # Loggear stdout/stderr a archivo para poder diagnosticar
    log_dir = PROJECT_DIR / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    flask_log = open(log_dir / "fast_local_server.log", "a", encoding="utf-8", buffering=1)
    flask_log.write(f"\n=== {datetime.now().isoformat(timespec='seconds')} - INICIO ===\n")
    subprocess.Popen(
        [pythonw, "fast_local_server.py"],
        cwd=str(PROJECT_DIR),
        env=env,
        creationflags=CREATE_NO_WINDOW,
        stdout=flask_log,
        stderr=flask_log,
        close_fds=True,
    )
    log("Flask relanzado")


def start_cloudflared():
    subprocess.Popen(
        [str(CLOUDFLARED), "tunnel", "run", "fast-mp"],
        creationflags=CREATE_NO_WINDOW,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        close_fds=True,
    )
    log("Cloudflared relanzado")


def main():
    if not is_flask_alive():
        kill_dead_pythonw()
        start_flask()
        time.sleep(2)

    if not is_cloudflared_running():
        start_cloudflared()


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        log(f"ERROR: {e}")
