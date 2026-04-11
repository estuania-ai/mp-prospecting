"""
WhatsApp Desktop Sender
Envia mensajes usando la app de escritorio de WhatsApp via pyautogui
Mas confiable que Selenium - usa la app nativa de Windows
"""

import os
import time
import random
import logging
import subprocess
import pyautogui
import pyperclip
import requests
import tempfile
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Configuracion pyautogui
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.3

# ── DELAYS HUMANIZADOS ────────────────────────────────────────
DELAY_PROFILES = [
    (30,  60,  0.15),
    (60,  90,  0.25),
    (90,  150, 0.35),
    (150, 240, 0.20),
    (240, 360, 0.05),
]

def weighted_delay(profiles):
    weights = [p[2] for p in profiles]
    total = sum(weights)
    r = random.uniform(0, total)
    cumulative = 0
    for mn, mx, w in profiles:
        cumulative += w
        if r <= cumulative:
            return random.uniform(mn, mx)
    return random.uniform(60, 120)

def human_delay():
    delay = weighted_delay(DELAY_PROFILES)
    final = max(30, delay + random.uniform(-5, 5))
    logger.info(f"Esperando {final:.0f}s antes del proximo mensaje...")
    time.sleep(final)

def micro_pause():
    time.sleep(random.uniform(0.3, 1.0))


# ── IMAGE CACHE ────────────────────────────────────────────────
_image_cache = {}

def download_image(url: str) -> str | None:
    if url in _image_cache:
        path = _image_cache[url]
        if os.path.exists(path):
            return path
    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        ext = '.png' if 'png' in url.lower() else '.jpg'
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext)
        tmp.write(resp.content)
        tmp.close()
        _image_cache[url] = tmp.name
        logger.info(f"Imagen descargada: {tmp.name}")
        return tmp.name
    except Exception as e:
        logger.error(f"Error descargando imagen: {e}")
        return None


# ── SESSION GUARD ─────────────────────────────────────────────
class SessionGuard:
    DAILY_LIMIT = 50
    WARN_THRESHOLD = 40

    def __init__(self):
        self.sent_today = 0
        self.session_date = datetime.now().date()
        self.consecutive_errors = 0

    def reset_if_new_day(self):
        today = datetime.now().date()
        if today != self.session_date:
            self.sent_today = 0
            self.session_date = today
            self.consecutive_errors = 0

    def can_send(self):
        self.reset_if_new_day()
        return self.sent_today < self.DAILY_LIMIT

    def register_sent(self):
        self.sent_today += 1
        self.consecutive_errors = 0
        logger.info(f"Mensaje {self.sent_today}/{self.DAILY_LIMIT} enviado hoy")
        if self.sent_today >= self.WARN_THRESHOLD:
            time.sleep(random.uniform(30, 60))

    def register_error(self, reason=""):
        self.consecutive_errors += 1
        logger.warning(f"Error #{self.consecutive_errors}: {reason}")

    def remaining(self):
        self.reset_if_new_day()
        return max(0, self.DAILY_LIMIT - self.sent_today)

    def get_extra_long_pause(self):
        if self.sent_today > 0 and self.sent_today % random.randint(10, 15) == 0:
            pause = random.uniform(300, 600)
            logger.info(f"Pausa larga: {pause/60:.1f} minutos")
            time.sleep(pause)


# ── WHATSAPP DESKTOP SENDER ───────────────────────────────────
class WhatsAppSender:

    def __init__(self):
        self.guard = SessionGuard()
        self._is_logged_in = True  # App desktop siempre logueada

    def start(self):
        """Abre WhatsApp Desktop si no esta abierto"""
        logger.info("Iniciando WhatsApp Desktop...")
        try:
            # Abrir WhatsApp via URL scheme
            os.startfile("whatsapp://")
            time.sleep(4)
            self._is_logged_in = True
            logger.info("WhatsApp Desktop listo")
            return True
        except Exception as e:
            logger.warning(f"No se pudo abrir via URL scheme: {e}")
            # Intentar abrir desde ruta comun
            paths = [
                os.path.expandvars(r"%LOCALAPPDATA%\WhatsApp\WhatsApp.exe"),
                os.path.expandvars(r"%APPDATA%\Microsoft\Windows\Start Menu\Programs\WhatsApp.lnk"),
            ]
            for p in paths:
                if os.path.exists(p):
                    subprocess.Popen([p])
                    time.sleep(4)
                    self._is_logged_in = True
                    return True
            self._is_logged_in = True
            return True

    def _open_chat_by_phone(self, phone: str) -> bool:
        """Abre chat con numero via URL scheme wa.me"""
        try:
            clean = phone.replace('+', '').replace(' ', '')
            url = f"whatsapp://send?phone={clean}"
            os.startfile(url)
            time.sleep(5)
            return True
        except Exception as e:
            logger.error(f"Error abriendo chat: {e}")
            return False

    def _send_image_and_text(self, phone: str, message: str, image_path: str) -> bool:
        """Envia imagen con caption via clipboard"""
        try:
            # Abrir chat
            if not self._open_chat_by_phone(phone):
                return False
            time.sleep(3)

            # Copiar imagen al clipboard usando PowerShell
            ps_cmd = f'Set-Clipboard -Path "{image_path}"'
            subprocess.run(['powershell', '-Command', ps_cmd], capture_output=True)
            time.sleep(1)

            # Pegar imagen (Ctrl+V)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(2)

            # Escribir caption
            # Limpiar el campo de caption y escribir
            pyperclip.copy(message)
            time.sleep(0.5)
            pyautogui.hotkey('ctrl', 'a')
            time.sleep(0.3)
            pyautogui.hotkey('ctrl', 'v')
            time.sleep(1)

            # Enviar
            pyautogui.press('enter')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error enviando imagen: {e}")
            return False

    def _send_text_only(self, phone: str, message: str) -> bool:
        """Envia mensaje de texto via URL scheme con texto precompletado"""
        try:
            import urllib.parse
            clean = phone.replace('+', '').replace(' ', '')
            # Usar wa.me con texto precompletado
            encoded = urllib.parse.quote(message)
            url = f"whatsapp://send?phone={clean}&text={encoded}"
            os.startfile(url)
            time.sleep(5)

            # Presionar Enter para enviar
            pyautogui.press('enter')
            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error enviando texto: {e}")
            return False

    def send_message(self, phone: str, message: str, image_url: str = None) -> dict:
        result = {
            'phone': phone,
            'success': False,
            'error': None,
            'timestamp': datetime.now().isoformat()
        }

        if not self.guard.can_send():
            result['error'] = 'daily_limit_reached'
            return result

        self.guard.get_extra_long_pause()

        try:
            time.sleep(random.uniform(1.0, 2.0))

            if image_url:
                image_path = download_image(image_url)
                if image_path:
                    success = self._send_image_and_text(phone, message, image_path)
                else:
                    success = self._send_text_only(phone, message)
            else:
                success = self._send_text_only(phone, message)

            if success:
                self.guard.register_sent()
                result['success'] = True
                logger.info(f"Mensaje enviado a {phone}")
            else:
                self.guard.register_error("Fallo envio")
                result['error'] = 'send_failed'

            return result

        except Exception as e:
            logger.error(f"Excepcion enviando a {phone}: {e}")
            self.guard.register_error(str(e))
            result['error'] = str(e)
            return result

    def send_batch(self, contacts: list, get_message_fn, get_image_fn=None) -> list:
        results = []
        total = min(len(contacts), self.guard.remaining())
        logger.info(f"Iniciando lote de {total} mensajes...")

        for i, contact in enumerate(contacts[:total]):
            phone = contact.get('phone', '')
            name  = contact.get('name', 'estimado/a')
            logger.info(f"[{i+1}/{total}] Enviando a {name} ({phone})")

            message   = get_message_fn(contact)
            image_url = get_image_fn(contact) if get_image_fn else None

            result = self.send_message(phone, message, image_url)
            result.update({'contact': contact, 'index': i+1, 'total': total})
            results.append(result)

            if i < total - 1:
                human_delay()

        success_count = sum(1 for r in results if r['success'])
        logger.info(f"Lote completado: {success_count}/{total} enviados")
        return results

    def quit(self):
        pass

    def get_status(self) -> dict:
        return {
            'logged_in': self._is_logged_in,
            'sent_today': self.guard.sent_today,
            'remaining': self.guard.remaining(),
            'blocked': False,
            'block_until': None,
        }


_sender_instance = None

def get_sender() -> WhatsAppSender:
    global _sender_instance
    if _sender_instance is None:
        _sender_instance = WhatsAppSender()
    return _sender_instance
