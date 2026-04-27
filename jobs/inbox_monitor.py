"""
Inbox Monitor — Playwright (Gmail Basic HTML view)
===================================================
Lee la bandeja de entrada cada 30 min y detecta:
  1. Respuestas de clientes  → actualiza estado a 'respondido'
  2. Rebotes (MAILER-DAEMON) → actualiza estado a 'rebotado'

Requiere sesión guardada (ejecutar setup_gmail_playwright.py una sola vez).
Sesión se guarda en: data/gmail_storage.json
"""
import logging
import pathlib
import threading
import re
from datetime import datetime
from database import get_db

logger = logging.getLogger(__name__)

BASE_DIR     = pathlib.Path(__file__).parent.parent
STORAGE_FILE = BASE_DIR / 'data' / 'gmail_storage.json'

# Patrones de rebote — inglés + español (Google Workspace Chile)
BOUNCE_SENDERS = {
    'mailer-daemon', 'postmaster', 'mail delivery subsystem',
    'delivery status notification', 'undeliverable', 'mail delivery failed',
}
BOUNCE_SUBJECTS = [
    # Inglés
    'delivery status notification', 'undeliverable', 'mail delivery failed',
    'returned mail', 'failure notice', 'delivery failure',
    'message not delivered', 'message delivery failed',
    # Español — Google Workspace en español (Chile/LATAM)
    'no se ha encontrado la dirección',
    'no se ha completado la entrega',
    'no se pudo entregar el mensaje',
    'no se ha podido entregar',
    'correo no entregado',
    'mensaje no entregado',
    'no se entregó el mensaje',
    'entrega fallida',
]

# Snippets de rebote (Google los pone en el cuerpo del correo)
BOUNCE_SNIPPETS = [
    'no se ha entregado a',
    'no se encontró el dominio',
    'couldn\'t be delivered',
    'was not delivered',
    'address not found',
]

MY_EMAIL = 'juansebastian.pinto@mercadolibre.cl'


# ── DB helpers ────────────────────────────────────────────────────────────────

def _load_known_emails() -> set:
    try:
        conn = get_db()
        rows = conn.execute(
            'SELECT LOWER(TRIM(email)) FROM et_contacts WHERE email IS NOT NULL'
        ).fetchall()
        conn.close()
        return {r[0] for r in rows if r[0]}
    except Exception:
        return set()


def _mark_replied(from_email: str, subject: str, snippet: str) -> bool:
    try:
        conn = get_db()
        row = conn.execute(
            'SELECT id, estado_interes, campaign_status FROM et_contacts '
            'WHERE LOWER(TRIM(email)) = ?', (from_email,)
        ).fetchone()
        if not row:
            conn.close()
            return False
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            '''UPDATE et_contacts
               SET email_replied   = 1,
                   estado_interes  = CASE WHEN estado_interes IN ('pendiente','no_enviado')
                                         THEN 'respondido' ELSE estado_interes END,
                   campaign_status = CASE WHEN campaign_status NOT IN ('cerrado','no_interesado','opt_out')
                                         THEN 'respondido' ELSE campaign_status END
               WHERE id = ?''',
            (row[0],)
        )
        conn.execute(
            '''INSERT OR IGNORE INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
               VALUES (?, 'reply', ?, ?, 'respondido')''',
            (row[0], now, f'Asunto: {subject[:100]} | {snippet[:200]}')
        )
        conn.commit()
        conn.close()
        logger.info(f'[InboxMonitor] Respuesta: {from_email} → contact_id={row[0]}')
        return True
    except Exception as e:
        logger.error(f'[InboxMonitor] Error marcando respuesta: {e}')
        return False


def _mark_bounced(recipient_email: str, subject: str, snippet: str) -> bool:
    try:
        conn = get_db()
        row = conn.execute(
            'SELECT id FROM et_contacts WHERE LOWER(TRIM(email)) = ?',
            (recipient_email.lower().strip(),)
        ).fetchone()
        if not row:
            conn.close()
            return False
        now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn.execute(
            'UPDATE et_contacts SET email_bounced=1, campaign_status=? WHERE id=?',
            ('rebotado', row[0])
        )
        conn.execute(
            '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
               VALUES (?, 'bounce', ?, ?, 'rebotado')''',
            (row[0], now, f'Rebote: {subject[:100]} | {snippet[:150]}')
        )
        conn.commit()
        conn.close()
        logger.info(f'[InboxMonitor] Rebote: {recipient_email} → contact_id={row[0]}')
        return True
    except Exception as e:
        logger.error(f'[InboxMonitor] Error marcando rebote: {e}')
        return False


def _extract_email(text: str) -> str:
    """Extrae la primera dirección email de un string."""
    m = re.search(r'[\w._%+\-]+@[\w.\-]+\.[a-zA-Z]{2,}', text)
    return m.group(0).lower() if m else text.lower().strip()


# ── Playwright reader ─────────────────────────────────────────────────────────

def _parse_inbox_html(html: str, known_emails: set) -> list:
    """
    Parsea el HTML de Gmail Basic (/mail/u/0/h/) y retorna lista de
    {'from': str, 'subject': str, 'snippet': str} para mensajes relevantes.
    """
    from html.parser import HTMLParser

    results = []

    class _Parser(HTMLParser):
        def __init__(self):
            super().__init__()
            self._in_row = False
            self._current = {}
            self._col = 0
            self._data_buf = ''

        def handle_starttag(self, tag, attrs):
            attr = dict(attrs)
            if tag == 'tr':
                self._in_row = True
                self._current = {}
                self._col = 0
            if tag == 'td' and self._in_row:
                self._col += 1
                self._data_buf = ''

        def handle_endtag(self, tag):
            if tag == 'td' and self._in_row:
                text = self._data_buf.strip()
                if self._col == 1:
                    self._current['from'] = text
                elif self._col == 2:
                    self._current['subject'] = text
                elif self._col == 3:
                    self._current['snippet'] = text
            elif tag == 'tr' and self._in_row:
                self._in_row = False
                if self._current.get('from'):
                    results.append(dict(self._current))

        def handle_data(self, data):
            if self._in_row:
                self._data_buf += data

    _Parser().feed(html)
    return results


CHROME_EXE         = r'C:\Program Files\Google\Chrome\Application\chrome.exe'
CHROME_PROFILE_DIR = r'C:\Users\juanspinto\AppData\Local\Google\Chrome\User Data'
CHROME_PROFILE     = 'Profile 8'


def _is_chrome_running() -> bool:
    """Devuelve True si hay algún proceso chrome.exe activo."""
    import subprocess
    r = subprocess.run('tasklist /FI "IMAGENAME eq chrome.exe" /NH',
                       shell=True, capture_output=True, text=True)
    return 'chrome.exe' in r.stdout


def _launch_chrome_for_inbox(p):
    """
    Lanza Chrome real (channel='chrome') con el perfil ML via launch_persistent_context.
    Chrome debe estar cerrado. Retorna (browser, page) o (None, None).
    """
    import pathlib
    if not pathlib.Path(CHROME_EXE).exists():
        return None, None
    try:
        ctx = p.chromium.launch_persistent_context(
            user_data_dir=CHROME_PROFILE_DIR,
            channel='chrome',
            headless=False,          # visible — necesario para que carguen extensiones de confianza
            args=[
                f'--profile-directory={CHROME_PROFILE}',
                '--no-first-run',
                '--no-default-browser-check',
                '--window-position=0,10000',   # ventana fuera de pantalla (invisible al usuario)
                '--window-size=1,1',
            ],
        )
        page = ctx.new_page()
        return ctx, page
    except Exception as e:
        logger.error(f'[InboxMonitor] Error al lanzar Chrome: {e}')
        return None, None


def _read_messages_from_page(page, max_messages: int) -> list:
    """
    Navega a Gmail Basic HTML y extrae mensajes via JS.
    Retorna lista de dicts con keys: from, subject, snippet.
    """
    page.goto('https://mail.google.com/mail/u/0/h/', wait_until='domcontentloaded', timeout=30_000)

    # Verificar acceso (CAA redirect va a admin.google.com)
    url = page.url
    if 'accounts.google.com' in url or 'admin.google.com' in url or 'signin' in url:
        return None  # señal de bloqueo

    # Esperar que cargue la tabla de mensajes
    try:
        page.wait_for_selector('table', timeout=10_000)
    except Exception:
        pass

    # Extraer filas — Gmail Basic HTML tiene tabla con columnas:
    # [0]=checkbox [1]=estrella [2]=remitente [3]=asunto-snippet [4]=fecha
    messages = page.evaluate(f'''() => {{
        var rows = [];
        var trs = document.querySelectorAll("table tr");
        trs.forEach(function(tr) {{
            var tds = tr.querySelectorAll("td");
            if (tds.length >= 4) {{
                var from   = (tds[2] ? tds[2].innerText.trim() : "");
                var subjTd = (tds[3] ? tds[3].innerText.trim() : "");
                var dashIdx = subjTd.indexOf(" - ");
                var subject = dashIdx >= 0 ? subjTd.substring(0, dashIdx).trim() : subjTd;
                var snippet = dashIdx >= 0 ? subjTd.substring(dashIdx + 3).trim() : "";
                if (from || subject) rows.push({{from: from, subject: subject, snippet: snippet}});
            }}
        }});
        return rows.slice(0, {max_messages});
    }}''')

    return messages or []


def check_inbox(max_messages: int = 100) -> dict:
    """
    Lee Gmail usando Chrome real (launch_persistent_context) para pasar CAA de ML.
    Solo corre cuando Chrome está cerrado — si está abierto, lo saltea sin error.
    """
    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        return {
            'replies': 0, 'bounces': 0, 'errors': 0,
            'status': 'sin_playwright',
            'message': 'Playwright no instalado. Ejecuta: pip install playwright && playwright install chromium'
        }

    # Si Chrome está abierto, saltear silenciosamente (no se puede usar el perfil)
    if _is_chrome_running():
        logger.info('[InboxMonitor] Chrome abierto — sync saltada (se ejecutará cuando Chrome esté cerrado)')
        return {
            'replies': 0, 'bounces': 0, 'errors': 0,
            'status': 'chrome_abierto',
            'message': 'Chrome está abierto. Ciérralo para que el sync pueda leer tu bandeja.'
        }

    known_emails = _load_known_emails()
    replies = bounces = errors = 0

    try:
        with sync_playwright() as p:
            ctx, page = _launch_chrome_for_inbox(p)

            if not ctx:
                return {
                    'replies': 0, 'bounces': 0, 'errors': 0,
                    'status': 'chrome_no_debug',
                    'message': 'No se pudo iniciar Chrome para leer el inbox.'
                }

            messages = _read_messages_from_page(page, max_messages)

            if messages is None:
                page.close()
                ctx.close()
                return {
                    'replies': 0, 'bounces': 0, 'errors': 0,
                    'status': 'acceso_denegado',
                    'message': 'Google bloqueó el acceso (CAA). Intenta nuevamente.'
                }

            logger.info(f'[InboxMonitor] {len(messages)} mensajes leídos')

            for msg in messages:
                try:
                    from_raw   = (msg.get('from') or '').lower()
                    subject    = (msg.get('subject') or '')
                    snippet    = (msg.get('snippet') or '')
                    subj_lower = subject.lower()
                    snip_lower = snippet.lower()

                    # Detectar rebote — subject/snippet en español o inglés
                    is_bounce = (
                        any(b in from_raw   for b in BOUNCE_SENDERS)  or
                        any(b in subj_lower for b in BOUNCE_SUBJECTS) or
                        any(b in snip_lower for b in BOUNCE_SNIPPETS)
                    )

                    if is_bounce:
                        # Google escribe: "Tu mensaje no se ha entregado a EMAIL@DOM porque..."
                        recipient = _extract_email(snippet) or _extract_email(subject)
                        if recipient and recipient != MY_EMAIL and recipient in known_emails:
                            if _mark_bounced(recipient, subject, snippet):
                                bounces += 1
                        continue

                    # Ignorar mis propios mensajes
                    from_email = _extract_email(from_raw)
                    if MY_EMAIL in from_email:
                        continue

                    # Detectar respuesta de contacto
                    if from_email in known_emails:
                        if _mark_replied(from_email, subject, snippet):
                            replies += 1

                except Exception as e:
                    logger.debug(f'[InboxMonitor] Error procesando mensaje: {e}')
                    errors += 1

            page.close()
            ctx.close()

    except Exception as e:
        logger.error(f'[InboxMonitor] Error general: {e}')
        return {'replies': 0, 'bounces': 0, 'errors': 1, 'status': 'error', 'message': str(e)}

    logger.info(f'[InboxMonitor] Completado: {replies} respuestas, {bounces} rebotes, {errors} errores')
    return {'replies': replies, 'bounces': bounces, 'errors': errors, 'status': 'ok'}


def check_inbox_in_thread():
    threading.Thread(target=check_inbox, daemon=True).start()
