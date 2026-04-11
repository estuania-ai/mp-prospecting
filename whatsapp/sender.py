"""
WhatsApp Sender - Sistema anti-bloqueo completo
Envia mensajes con imagen descargada desde URL segun categoria del rubro
"""

import os
import time
import random
import logging
import requests
import tempfile
from datetime import datetime, timedelta
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.common.exceptions import (
    TimeoutException, NoSuchElementException, WebDriverException
)

logger = logging.getLogger(__name__)

# ── DELAYS HUMANIZADOS ────────────────────────────────────────
DELAY_PROFILES = [
    (30,  60,  0.15),
    (60,  90,  0.25),
    (90,  150, 0.35),
    (150, 240, 0.20),
    (240, 360, 0.05),
]

TYPING_PROFILES = [
    (1.5, 3.0, 0.30),
    (3.0, 5.0, 0.45),
    (5.0, 8.0, 0.25),
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
    return random.uniform(profiles[-1][0], profiles[-1][1])

def human_delay():
    delay = weighted_delay(DELAY_PROFILES)
    final = max(30, delay + random.uniform(-5, 5))
    logger.info(f"Esperando {final:.0f}s antes del proximo mensaje...")
    time.sleep(final)

def typing_delay():
    time.sleep(weighted_delay(TYPING_PROFILES))

def micro_pause():
    time.sleep(random.uniform(0.5, 2.0))


# ── IMAGE CACHE ────────────────────────────────────────────────
_image_cache = {}

def download_image(url: str) -> str | None:
    """Descarga imagen desde URL, la guarda en temp y retorna el path local"""
    if url in _image_cache:
        path = _image_cache[url]
        if os.path.exists(path):
            return path

    try:
        resp = requests.get(url, timeout=20)
        resp.raise_for_status()
        ext = '.jpg'
        if 'png' in url.lower(): ext = '.png'
        tmp = tempfile.NamedTemporaryFile(delete=False, suffix=ext, dir=tempfile.gettempdir())
        tmp.write(resp.content)
        tmp.close()
        _image_cache[url] = tmp.name
        logger.info(f"Imagen descargada: {url} -> {tmp.name}")
        return tmp.name
    except Exception as e:
        logger.error(f"Error descargando imagen {url}: {e}")
        return None


# ── SESSION GUARD ─────────────────────────────────────────────
class SessionGuard:
    DAILY_LIMIT = 50
    BLOCK_COOLDOWN_HOURS = 24
    WARN_THRESHOLD = 40

    def __init__(self):
        self.sent_today = 0
        self.session_date = datetime.now().date()
        self.blocked = False
        self.block_until = None
        self.consecutive_errors = 0

    def reset_if_new_day(self):
        today = datetime.now().date()
        if today != self.session_date:
            self.sent_today = 0
            self.session_date = today
            self.blocked = False
            self.block_until = None
            self.consecutive_errors = 0

    def can_send(self):
        self.reset_if_new_day()
        if self.blocked and self.block_until:
            if datetime.now() < self.block_until:
                return False
            else:
                self.blocked = False
        return self.sent_today < self.DAILY_LIMIT

    def register_sent(self):
        self.sent_today += 1
        self.consecutive_errors = 0
        logger.info(f"Mensaje {self.sent_today}/{self.DAILY_LIMIT} enviado hoy")
        if self.sent_today >= self.WARN_THRESHOLD:
            extra = random.uniform(30, 60)
            logger.info(f"Cerca del limite diario - pausa extra {extra:.0f}s")
            time.sleep(extra)

    def register_error(self, reason=""):
        self.consecutive_errors += 1
        logger.warning(f"Error #{self.consecutive_errors}: {reason}")
        if self.consecutive_errors >= 3:
            self.blocked = True
            self.block_until = datetime.now() + timedelta(hours=1)
            logger.error("Multiples errores - pausa de 1 hora")

    def register_block(self):
        self.blocked = True
        self.block_until = datetime.now() + timedelta(hours=self.BLOCK_COOLDOWN_HOURS)
        logger.error(f"BLOQUEO DETECTADO - pausa hasta {self.block_until}")

    def remaining(self):
        self.reset_if_new_day()
        return max(0, self.DAILY_LIMIT - self.sent_today)

    def get_extra_long_pause(self):
        if self.sent_today > 0 and self.sent_today % random.randint(10, 15) == 0:
            pause = random.uniform(300, 600)
            logger.info(f"Pausa larga: {pause/60:.1f} minutos")
            time.sleep(pause)


# ── WHATSAPP SENDER ───────────────────────────────────────────
class WhatsAppSender:

    WHATSAPP_URL = "https://web.whatsapp.com"
    PROFILE_DIR  = os.path.join(os.path.expanduser("~"), "whatsapp_profile_mp")

    XPATHS = {
        'message_box':     '//div[@contenteditable="true"][@data-tab="10"]',
        'message_box_alt': '//div[@aria-label="Escribe un mensaje"]',
        'send_btn':        '//button[@aria-label="Enviar"]',
        'attach_btn':      '//div[@title="Adjuntar"]',
        'attach_image':    '//input[@accept="image/*,video/mp4,video/3gpp,video/quicktime"]',
        'caption_box':     '//div[@aria-label="Agrega un pie de foto o descripcion"]',
        'caption_box2':    '//div[@aria-label="Add a caption"]',
        'logged_in':       '//div[@aria-label="Lista de chats"]',
        'ban_warning':     '//div[contains(text(),"cuenta ha sido suspendida")]',
    }

    def __init__(self):
        self.driver = None
        self.wait   = None
        self.guard  = SessionGuard()
        self._is_logged_in = False

    def _get_chrome_options(self):
        opts = Options()
        opts.add_argument(f"--user-data-dir={self.PROFILE_DIR}")
        opts.add_argument("--profile-directory=Default")
        opts.add_argument("--no-sandbox")
        opts.add_argument("--disable-dev-shm-usage")
        opts.add_argument("--disable-blink-features=AutomationControlled")
        opts.add_experimental_option("excludeSwitches", ["enable-automation"])
        opts.add_experimental_option("useAutomationExtension", False)
        opts.add_argument("--window-size=1280,900")
        opts.add_argument("--lang=es-CL")
        opts.add_argument(
            "--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36"
        )
        return opts

    def start(self):
        logger.info("Iniciando WhatsApp Web...")
        try:
            opts = self._get_chrome_options()
            self.driver = webdriver.Chrome(options=opts)
            self.driver.execute_script(
                "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
            )
            self.wait = WebDriverWait(self.driver, 60)
            self.driver.get(self.WHATSAPP_URL)
            self._wait_for_login()
            return True
        except WebDriverException as e:
            logger.error(f"Error iniciando Chrome: {e}")
            return False

    def _wait_for_login(self):
        logger.info("Esperando login de WhatsApp Web...")
        try:
            self.wait = WebDriverWait(self.driver, 120)
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, self.XPATHS['logged_in']))
            )
            self._is_logged_in = True
            logger.info("WhatsApp Web conectado OK")
            time.sleep(3)
        except TimeoutException:
            logger.error("Timeout esperando login. Escanea el QR manualmente.")
            raise

    def _check_ban(self):
        try:
            ban = self.driver.find_elements(By.XPATH, self.XPATHS['ban_warning'])
            if ban:
                self.guard.register_block()
                return True
        except Exception:
            pass
        return False

    def _open_chat(self, phone: str) -> bool:
        try:
            clean = ''.join(filter(str.isdigit, phone))
            url = f"https://web.whatsapp.com/send?phone={clean}&text="
            self.driver.get(url)
            self.wait = WebDriverWait(self.driver, 30)
            self.wait.until(
                EC.presence_of_element_located((By.XPATH, self.XPATHS['message_box']))
            )
            micro_pause()
            return True
        except TimeoutException:
            try:
                self.driver.find_element(By.XPATH, self.XPATHS['message_box_alt'])
                return True
            except NoSuchElementException:
                logger.warning(f"No se pudo abrir chat con {phone}")
                return False
        except Exception as e:
            logger.error(f"Error abriendo chat {phone}: {e}")
            return False

    def _type_humanized(self, element, text: str):
        chunks = [text[i:i+20] for i in range(0, len(text), 20)]
        for chunk in chunks:
            element.send_keys(chunk)
            time.sleep(random.uniform(0.05, 0.2))

    def _send_text_only(self, msg_box, text: str) -> bool:
        try:
            lines = text.split('\n')
            for i, line in enumerate(lines):
                if line:
                    msg_box.send_keys(line)
                    time.sleep(random.uniform(0.05, 0.15))
                if i < len(lines) - 1:
                    msg_box.send_keys(Keys.SHIFT + Keys.ENTER)
                    time.sleep(random.uniform(0.1, 0.3))
            micro_pause()
            try:
                send_btn = self.driver.find_element(By.XPATH, self.XPATHS['send_btn'])
                send_btn.click()
            except NoSuchElementException:
                msg_box.send_keys(Keys.ENTER)
            time.sleep(1.5)
            return True
        except Exception as e:
            logger.error(f"Error enviando texto: {e}")
            return False

    def _send_with_image(self, image_path: str, caption: str) -> bool:
        """Envia imagen con caption (el mensaje va como pie de foto)"""
        try:
            # Click en boton adjuntar
            attach_btn = self.wait.until(
                EC.element_to_be_clickable((By.XPATH, self.XPATHS['attach_btn']))
            )
            attach_btn.click()
            micro_pause()

            # Input de archivo
            file_input = self.wait.until(
                EC.presence_of_element_located((By.XPATH, self.XPATHS['attach_image']))
            )
            file_input.send_keys(os.path.abspath(image_path))
            time.sleep(3)

            # Caption field - probar dos selectores posibles
            caption_box = None
            for xpath in [self.XPATHS['caption_box'], self.XPATHS['caption_box2']]:
                try:
                    caption_box = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, xpath))
                    )
                    break
                except TimeoutException:
                    continue

            if caption_box:
                typing_delay()
                self._type_humanized(caption_box, caption)
                micro_pause()
                caption_box.send_keys(Keys.ENTER)
            else:
                # Si no hay campo de caption, enviar sin texto
                logger.warning("No se encontro campo de caption, enviando imagen sola")
                send_btn = self.wait.until(
                    EC.element_to_be_clickable((By.XPATH, self.XPATHS['send_btn']))
                )
                send_btn.click()

            time.sleep(2)
            return True

        except Exception as e:
            logger.error(f"Error enviando imagen: {e}")
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

        if self._check_ban():
            result['error'] = 'account_banned'
            return result

        self.guard.get_extra_long_pause()

        try:
            if not self._open_chat(phone):
                self.guard.register_error(f"No se pudo abrir chat con {phone}")
                result['error'] = 'chat_open_failed'
                return result

            time.sleep(random.uniform(1.0, 3.0))

            if image_url:
                image_path = download_image(image_url)
                if image_path:
                    success = self._send_with_image(image_path, message)
                else:
                    # Fallback a solo texto si falla la imagen
                    logger.warning("Imagen no disponible, enviando solo texto")
                    msg_box = self.wait.until(
                        EC.presence_of_element_located((By.XPATH, self.XPATHS['message_box']))
                    )
                    typing_delay()
                    success = self._send_text_only(msg_box, message)
            else:
                msg_box = self.wait.until(
                    EC.presence_of_element_located((By.XPATH, self.XPATHS['message_box']))
                )
                typing_delay()
                success = self._send_text_only(msg_box, message)

            if success:
                self.guard.register_sent()
                result['success'] = True
                logger.info(f"Mensaje enviado a {phone}")
            else:
                self.guard.register_error("Fallo en envio")
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
        if self.driver:
            try:
                self.driver.quit()
                logger.info("Driver cerrado")
            except Exception:
                pass

    def get_status(self) -> dict:
        return {
            'logged_in': self._is_logged_in,
            'sent_today': self.guard.sent_today,
            'remaining': self.guard.remaining(),
            'blocked': self.guard.blocked,
            'block_until': str(self.guard.block_until) if self.guard.block_until else None,
        }


_sender_instance = None

def get_sender() -> WhatsAppSender:
    global _sender_instance
    if _sender_instance is None:
        _sender_instance = WhatsAppSender()
    return _sender_instance
