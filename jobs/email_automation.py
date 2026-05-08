"""
Email Automation Jobs
- Prospección diaria: 100 emails/día distribuidos en 14 rubros y comunas
- Follow-up automático: 48h sin respuesta → seguimiento 48h, 96h → seguimiento 96h, luego 'no_responde'
"""
import logging
import asyncio
import threading
import pathlib
from datetime import datetime, timedelta
from database import get_db

logger = logging.getLogger(__name__)


# ── PER-USER SMTP RESOLVER ────────────────────────────────────────
# Cada Sales tiene sus credenciales SMTP encriptadas + firma personalizada.
# El cache evita decrypt+IO en cada email del lote.
_USER_CREDS_CACHE: dict[int, dict] = {}

def _resolve_user_creds(user_id: int) -> dict | None:
    """
    Devuelve dict con creds SMTP del usuario (o None si está incompleto).
    { 'smtp_user', 'smtp_pass', 'from_email', 'from_name', 'sig_bytes' }
    """
    if user_id in _USER_CREDS_CACHE:
        return _USER_CREDS_CACHE[user_id]

    try:
        from secure_storage import decrypt
    except Exception as e:
        logger.error(f"[Email per-user] secure_storage no disponible: {e}")
        return None

    conn = get_db()
    row = conn.execute(
        '''SELECT smtp_user, smtp_pass_enc, name, sig_title, sig_phone, sig_photo_path
           FROM users WHERE id = ?''',
        (user_id,)
    ).fetchone()
    conn.close()
    if not row:
        return None

    smtp_user = (row['smtp_user'] or '').strip()
    enc       = (row['smtp_pass_enc'] or '').strip()
    if not smtp_user or not enc:
        return None
    try:
        smtp_pass = decrypt(enc)
    except Exception as e:
        logger.error(f"[Email per-user] decrypt falló user_id={user_id}: {e}")
        return None
    if not smtp_pass:
        return None

    sig_bytes = None
    sig_path = (row['sig_photo_path'] or '').strip()
    if sig_path:
        try:
            full = pathlib.Path(__file__).parent.parent / 'static' / sig_path
            if full.exists():
                sig_bytes = full.read_bytes()
        except Exception as e:
            logger.warning(f"[Email per-user] no se pudo leer firma: {e}")

    creds = {
        'smtp_user':  smtp_user,
        'smtp_pass':  smtp_pass,
        'from_email': smtp_user,
        'from_name':  (row['name'] or smtp_user.split('@')[0]),
        'sig_bytes':  sig_bytes,
    }
    _USER_CREDS_CACHE[user_id] = creds
    return creds


def _invalidate_user_creds_cache(user_id: int | None = None):
    """Llamar cuando un usuario actualiza su SMTP/firma."""
    if user_id is None:
        _USER_CREDS_CACHE.clear()
    else:
        _USER_CREDS_CACHE.pop(user_id, None)

# ── Fix 1: RUBROS_FALLBACK hardcodeado solo como respaldo ─────────────────────
# La fuente de verdad son los rubros en et_rubro_templates (ventana Campañas).
# Se carga dinámicamente en _get_active_rubros() para que al agregar un template
# nuevo el scraping lo capture automáticamente sin tocar código.
RUBROS_FALLBACK = [
    'cafetería', 'pastelería', 'sushi', 'emporio', 'clínica dental',
    'pizzería', 'librería', 'veterinaria', 'florería', 'oftalmología',
    'tienda de muebles', 'lubricentro', 'frenos', 'spa',
    'gimnasio', 'clínica de belleza', 'restaurant de pollos asados',
]

# ── Fix 3: COMUNAS_SANTIAGO — única fuente válida de comunas ──────────────────
# Cualquier valor fuera de esta lista ("Sin clasificar", "Puente Alto",
# "Santiago, Recoleta", etc.) queda bloqueado antes de llegar a Google.
COMUNAS_SANTIAGO = [
    'Santiago Centro', 'Providencia', 'Las Condes', 'Vitacura', 'La Florida',
    'Maipú', 'Pudahuel', 'Quilicura', 'Huechuraba', 'Recoleta',
    'Independencia', 'Conchalí', 'Renca', 'Cerro Navia', 'Lo Prado',
    'Quinta Normal', 'Estación Central', 'Cerrillos', 'Peñalolén',
    'Macul', 'Ñuñoa', 'La Reina', 'Lo Barnechea', 'Colina',
    'San Bernardo', 'El Bosque', 'La Granja', 'La Pintana',
    'San Ramón', 'Pedro Aguirre Cerda', 'Lo Espejo', 'Talagante',
    'Padre Hurtado', 'Peñaflor', 'Melipilla', 'Pirque', 'Buin',
    'Calera de Tango', 'Lampa', 'Til Til', 'Puente Alto',
]
_COMUNAS_LOWER = {c.lower() for c in COMUNAS_SANTIAGO}

EMAILS_PER_DAY = 100

# ── Fix 2: QUERY_VARIANTS con Chile/Santiago + variantes site:.cl ─────────────
# Todas las queries incluyen "Santiago Chile" para forzar resultados chilenos.
# Las variantes con site:.cl devuelven directamente dominios .cl.
QUERY_VARIANTS = [
    '{rubro} {comuna} Santiago Chile contacto email',
    '{rubro} {comuna} Santiago Chile correo sitio web',
    'site:.cl {rubro} {comuna} contacto email',
    '{rubro} en {comuna} Santiago de Chile email contacto',
    'site:.cl {rubro} {comuna} correo electronico',
]


def _get_active_rubros() -> list[str]:
    """
    Fix 1: Carga los rubros activos desde et_rubro_templates (fuente de verdad).
    Si agregas un nuevo template en la ventana Campañas, el scraping lo captura
    automáticamente en el próximo job sin tocar código.
    Fallback a RUBROS_FALLBACK si la DB no está disponible.
    """
    try:
        conn = get_db()
        rows = conn.execute(
            'SELECT rubro FROM et_rubro_templates ORDER BY id'
        ).fetchall()
        conn.close()
        if rows:
            return [r['rubro'] for r in rows]
    except Exception:
        pass
    return RUBROS_FALLBACK


def _get_least_prospected_comunas(rubro: str, n: int = 2) -> list[str]:
    """
    Retorna las n comunas con MENOS contactos enviados para este rubro.
    Usa conteo real (no solo presencia) para rotar correctamente entre comunas.
    """
    conn = get_db()
    counts = conn.execute(
        '''SELECT LOWER(TRIM(comuna)) as c, COUNT(*) as cnt
           FROM et_contacts WHERE rubro LIKE ?
           GROUP BY LOWER(TRIM(comuna))''',
        (f'%{rubro}%',)
    ).fetchall()
    conn.close()
    count_map = {r['c']: r['cnt'] for r in counts if r['c']}
    # Ordenar: menos contactos primero; empate → orden alfabético para reproducibilidad
    return sorted(COMUNAS_SANTIAGO, key=lambda c: (count_map.get(c.lower(), 0), c))[:n]


def _get_query_variant(rubro: str, comuna: str) -> str:
    """
    Elige una variante de query diferente cada vez que se repite el par rubro+comuna,
    para obtener resultados distintos de Google y llegar a nuevos negocios.
    """
    conn = get_db()
    # Contar cuántas variantes distintas se han usado ya para este par
    count = conn.execute(
        '''SELECT COUNT(DISTINCT source_query) FROM et_contacts
           WHERE rubro LIKE ? AND LOWER(TRIM(comuna)) = ?''',
        (f'%{rubro}%', comuna.lower().strip())
    ).fetchone()[0]
    conn.close()
    variant = QUERY_VARIANTS[count % len(QUERY_VARIANTS)]
    return variant.replace('{rubro}', rubro).replace('{comuna}', comuna)


def _get_template_for_rubro(rubro: str) -> dict:
    """
    Prioriza el contenido premium de RUBRO_EMAIL_CONTENT (email_tool.py).
    Fallback: tabla et_rubro_templates en BD.
    """
    try:
        from routes.email_tool import _get_rubro_content
        c = _get_rubro_content(rubro)
        if c:
            return {
                'subject': c.get('subject', f'Mercado Pago para tu {rubro}'),
                'body': c.get('body', f'Hola {{nombre}},\n\nTe escribo desde Mercado Pago.\n\n¿Conversamos esta semana?'),
            }
    except Exception:
        pass

    # Fallback BD
    conn = get_db()
    row = conn.execute(
        'SELECT subject, body FROM et_rubro_templates WHERE rubro LIKE ? LIMIT 1',
        (f'%{rubro.split()[0]}%',)
    ).fetchone()
    conn.close()
    if row:
        return {'subject': row['subject'], 'body': row['body']}

    return {
        'subject': f'Moderniza los cobros de tu {rubro} con Mercado Pago',
        'body': (
            f'Hola {{nombre}},\n\n'
            f'Me comunico desde Mercado Pago para presentarte el Smart Point, '
            f'la solución de cobro ideal para tu {rubro}.\n\n'
            f'¿Conversamos esta semana?\n\nSaludos,\nJuan Sebastián Pinto\nEjecutivo Mercado Pago'
        ),
    }


def _send_email(to_email: str, subject: str, body: str,
                rubro: str = '', contact_name: str = '',
                for_user_id: int | None = None) -> bool:
    """
    Delega a _send_smtp de email_tool para enviar el HTML animado completo.
    Si se pasa `for_user_id`:
      - Owner → usa env vars legacy (SMTP_USER/SMTP_PASS), sin firma per-user.
      - Sales/TL → resuelve sus creds; si no las tiene, skipea (no spoofea
        desde el SMTP del Owner).
    """
    import os
    from routes.email_tool import _send_smtp

    booking_url = os.getenv(
        'BOOKING_URL',
        'https://calendly.com/juansebastian-pinto/mercadopago'
    )
    user_creds = None
    if for_user_id:
        conn = get_db()
        urow = conn.execute(
            "SELECT role FROM users WHERE id = ?", (for_user_id,)
        ).fetchone()
        conn.close()
        if urow and urow['role'] == 'owner':
            # Owner mantiene flujo histórico: env vars + firma estática
            user_creds = None
        else:
            user_creds = _resolve_user_creds(for_user_id)
            if not user_creds:
                logger.warning(
                    f"[EmailAuto] user_id={for_user_id} (Sales/TL) sin SMTP — no se envía"
                )
                return False

    result = _send_smtp(
        to_email=to_email,
        subject=subject,
        body_text=body,
        rubro=rubro,
        contact_name=contact_name,
        booking_url=booking_url,
        user_creds=user_creds,
    )
    if not result.get('ok'):
        logger.error(f'[EmailAuto] Error enviando a {to_email}: {result.get("error")}')
    return result.get('ok', False)


async def _scrape_rubro_comuna(rubro: str, comuna: str, max_results: int,
                               send_emails: bool = True) -> int:
    """
    Scrapea Google para rubro+comuna y guarda contactos nuevos.
    - send_emails=True  → guarda como 'enviado' y manda el email inmediatamente (modo legacy).
    - send_emails=False → guarda como 'pendiente' sin enviar (modo scraping puro para job 08:00).
    - Usa variante de query para evitar repetir la misma búsqueda.
    - Saltar dominios ya scrapeados (deduplicación por website).
    - Saltar emails ya en la DB (deduplicación por email).
    Retorna cantidad de contactos guardados (o emails enviados si send_emails=True).
    """
    from playwright.async_api import async_playwright
    import re
    from urllib.parse import urlparse

    EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.I)

    # Fix 4: Dominios genéricos permitidos para negocios chilenos sin dominio .cl
    ALLOWED_GENERIC_DOMAINS = {
        'gmail.com', 'googlemail.com',
        'hotmail.com', 'hotmail.cl', 'hotmail.es',
        'outlook.com', 'outlook.cl',
        'yahoo.com', 'yahoo.es', 'yahoo.cl',
        'live.com', 'live.cl',
        'icloud.com',
    }
    # TLDs extranjeros que jamás corresponden a un negocio chileno prospectable
    BLOCKED_TLDS = {
        '.es', '.mx', '.com.mx', '.ar', '.com.ar', '.pe', '.co', '.com.co',
        '.uk', '.co.uk', '.de', '.fr', '.it', '.br', '.com.br', '.pt',
        '.us', '.ca', '.au', '.com.au', '.nz', '.in', '.kr', '.jp',
        '.eu', '.io', '.org', '.edu',  # educación y org rara vez son pymes chilenas
    }
    SKIP_DOMAINS = {
        'sentry.io', 'wixpress.com', 'example.com', 'domain.com',
        'googleapis.com', 'gstatic.com', 'w3.org', 'schema.org',
        'mercadopago.com', 'mercadolibre.com', 'facebook.com',
        'instagram.com', 'twitter.com', 'youtube.com', 'google.com', 'google.cl',
        'email.com', 'correo.com', 'misitio.com', 'midominio.com',
        'tudominio.com', 'tuemail.com', 'miemail.com', 'mail.com',
        'dominio.com', 'sitio.com', 'empresa.com', 'miempresa.com',
        'yoursite.com', 'yourcompany.com', 'website.com', 'webpage.com',
        'restaurantdemo.com', 'namesnack.com', 'latercera.com',
        'munistgo.cl',   # municipalidades — no son prospectos
    }
    # Extensiones de archivo que el regex puede confundir con emails
    FILE_EXTENSIONS = {
        '.png', '.jpg', '.jpeg', '.svg', '.gif', '.webp', '.ico',
        '.pdf', '.doc', '.docx', '.xls', '.xlsx', '.zip', '.mp4',
        '.mov', '.mp3', '.wav', '.css', '.js', '.json', '.xml',
    }
    SKIP_LOCAL_PARTS = {
        'tu', 'your', 'me', 'mi', 'test', 'demo', 'sample',
        'user', 'usuario', 'email', 'correo', 'nombre', 'name',
        'hello', 'hola', 'info2', 'u003e',
    }
    SKIP_PREFIXES = ('noreply', 'no-reply', 'donotreply', 'mailer',
                     'bounce', 'spam', 'webmaster', 'postmaster',
                     'admin', 'root', 'abuse', 'support', 'sales',
                     'press', 'media', 'pr@', 'legal', 'privacy')

    def clean_emails(emails):
        from urllib.parse import unquote
        result = []
        for e in emails:
            e = unquote(e).lower().strip()
            parts = e.split('@')
            if len(parts) != 2:
                continue
            local, domain = parts[0], parts[1]

            # Bloquear si el "dominio" termina en extensión de archivo
            if any(domain.endswith(ext) for ext in FILE_EXTENSIONS):
                continue
            # Bloquear dominios en lista negra
            if domain in SKIP_DOMAINS:
                continue
            # Fix 4: Filtro geográfico — solo .cl O dominios genéricos conocidos
            is_cl = domain.endswith('.cl')
            is_generic = domain in ALLOWED_GENERIC_DOMAINS
            has_blocked_tld = any(domain.endswith(tld) for tld in BLOCKED_TLDS)
            if not is_cl and not is_generic:
                continue   # descartar .es, .mx, .com.ar, .br, .eu, etc.
            if has_blocked_tld:
                continue
            # Bloquear partes locales inútiles
            if local in SKIP_LOCAL_PARTS:
                continue
            if any(local.startswith(p.rstrip('@')) for p in SKIP_PREFIXES):
                continue
            # Largo mínimo razonable
            if len(local) < 3 or '.' not in domain:
                continue
            if e not in result:
                result.append(e)
        return result

    # Elegir variante de query según cuántas veces ya se buscó este par
    query = _get_query_variant(rubro, comuna)
    logger.info(f'[EmailAuto] Query: "{query}"')

    tpl  = _get_template_for_rubro(rubro)
    sent = 0
    conn = get_db()

    # Pre-cargar dominios ya scrapeados para este rubro+comuna → evitar re-visitar mismos sitios
    already_scraped_rows = conn.execute(
        '''SELECT LOWER(website) as w FROM et_contacts
           WHERE rubro LIKE ? AND LOWER(TRIM(comuna)) = ?
           AND website IS NOT NULL AND website != ""''',
        (f'%{rubro}%', comuna.lower().strip())
    ).fetchall()
    scraped_domains = set()
    for r in already_scraped_rows:
        try:
            d = urlparse(r['w']).netloc.lower().replace('www.', '')
            if d:
                scraped_domains.add(d)
        except Exception:
            pass

    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-dev-shm-usage',
                '--disable-setuid-sandbox',
                '--disable-extensions',
                '--disable-background-networking',
                '--disable-default-apps',
                '--no-first-run',
            ]
            # Removido --single-process: inestable en Windows, causa crashes
            # Removido --disable-gpu y --disable-software-rasterizer: innecesarios en headless moderno
        )
        context = await browser.new_context(
            locale='es-CL',
            user_agent=(
                'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                'AppleWebKit/537.36 (KHTML, like Gecko) '
                'Chrome/124.0.0.0 Safari/537.36'
            )
        )
        page = await context.new_page()

        try:
            # Fix 5: google.cl + gl=cl&hl=es fuerza resultados de Chile
            search_url = (
                f'https://www.google.cl/search'
                f'?q={query.replace(" ", "+")}'
                f'&num=30&gl=cl&hl=es'
            )
            await page.goto(search_url, timeout=20_000)
            await asyncio.sleep(2)

            try:
                await page.get_by_role('button', name=re.compile('Aceptar|Accept|Rechazar|Decline', re.I)).first.click(timeout=3_000)
            except Exception:
                pass

            links = await page.evaluate("""
                () => {
                    const anchors = [...document.querySelectorAll('#search a[href]')];
                    const urls = [];
                    const BLOCKED = ['google.', 'youtube.', 'facebook.', 'instagram.',
                                     'twitter.', 'linkedin.', 'tiktok.', 'wikipedia.'];
                    for (const a of anchors) {
                        const href = a.href;
                        if (href && href.startsWith('http') &&
                            !BLOCKED.some(b => href.includes(b))) {
                            const clean = href.split('&')[0].split('#')[0];
                            if (!urls.includes(clean)) urls.push(clean);
                        }
                    }
                    return urls.slice(0, 30);
                }
            """)

            new_urls = []
            for url in links:
                try:
                    domain = urlparse(url).netloc.lower().replace('www.', '')
                    if domain and domain not in scraped_domains:
                        new_urls.append(url)
                        scraped_domains.add(domain)   # marcar para no repetir en esta sesión
                except Exception:
                    new_urls.append(url)

            logger.info(f'[EmailAuto] {len(links)} URLs encontradas, {len(new_urls)} nuevas (sin scraped_domains)')

            for url in new_urls[:max(max_results, 15)]:
                try:
                    await page.goto(url, timeout=12_000, wait_until='domcontentloaded')
                    title = await page.title()
                    business_name = title.split('|')[0].split('-')[0].strip()[:80]
                    html  = await page.content()
                    emails = clean_emails(EMAIL_RE.findall(html))

                    if not emails:
                        parsed = urlparse(url)
                        base   = f"{parsed.scheme}://{parsed.netloc}"
                        for path in ['/contacto', '/contact', '/contactanos', '/nosotros', '/about', '/quienes-somos']:
                            try:
                                await page.goto(base + path, timeout=8_000, wait_until='domcontentloaded')
                                html2  = await page.content()
                                emails = clean_emails(EMAIL_RE.findall(html2))
                                if emails:
                                    break
                            except Exception:
                                continue

                    for email in emails[:2]:
                        # Saltar si ya existe en la DB (enviado o no)
                        existing = conn.execute(
                            'SELECT id FROM et_contacts WHERE email = ?', (email,)
                        ).fetchone()
                        if existing:
                            logger.debug(f'[EmailAuto] Saltado (ya existe): {email}')
                            continue

                        now         = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                        followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')

                        if send_emails:
                            # Modo legacy: guardar como enviado + mandar email ahora
                            conn.execute(
                                '''INSERT INTO et_contacts
                                   (business_name, email, website, rubro, ciudad, comuna,
                                    source_query, created_at, campaign_status, fecha_envio,
                                    proximo_seguimiento)
                                   VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                                (business_name, email, url, rubro, 'Santiago', comuna,
                                 query, now, 'enviado', now, followup_dt)
                            )
                            conn.commit()
                            subject = tpl['subject']
                            body    = tpl['body'].replace('{nombre}', business_name)
                            ok = _send_email(email, subject, body,
                                             rubro=rubro, contact_name=business_name)
                            if ok:
                                sent += 1
                                logger.info(f'[EmailAuto] Enviado a {email} ({rubro}, {comuna})')
                            else:
                                conn.execute(
                                    "UPDATE et_contacts SET campaign_status='no_enviado', fecha_envio=NULL WHERE email=?",
                                    (email,)
                                )
                                conn.commit()
                        else:
                            # Modo scraping puro: guardar como pendiente, email_daily lo enviará a las 11:00
                            conn.execute(
                                '''INSERT INTO et_contacts
                                   (business_name, email, website, rubro, ciudad, comuna,
                                    source_query, created_at, campaign_status)
                                   VALUES (?,?,?,?,?,?,?,?,?)''',
                                (business_name, email, url, rubro, 'Santiago', comuna,
                                 query, now, 'pendiente')
                            )
                            conn.commit()
                            sent += 1
                            logger.info(f'[EmailAuto] Guardado pendiente: {email} ({rubro}, {comuna})')

                except Exception as e:
                    logger.debug(f'[EmailAuto] Error en {url}: {e}')
                    continue

                await asyncio.sleep(2)

        except Exception as e:
            logger.error(f'[EmailAuto] Error scraping {rubro}/{comuna}: {e}')
        finally:
            await browser.close()

    conn.close()
    return sent


def _run_async(coro):
    """
    Ejecuta una coroutine en un event loop limpio.
    NOTA: las coroutines Python solo se pueden ejecutar UNA VEZ, por lo que
    _run_async NO reintenta — el reintento debe hacerse en el caller creando
    una coroutine FRESCA en cada intento.
    """
    import time
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        # Cancelar tasks pendientes antes de cerrar (evita "Task was destroyed but it is pending")
        try:
            pending = asyncio.all_tasks(loop)
            if pending:
                for t in pending:
                    t.cancel()
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
        except Exception:
            pass
        loop.close()
        asyncio.set_event_loop(None)
        time.sleep(1)   # pausa mínima para que Chrome/OS libere el proceso


# ── Filtros compartidos de email y URL ───────────────────────────────────────

# Dominios de directorio/agregador: los visitamos pero NO extraemos sus propios
# emails (son de la plataforma, no del negocio que buscamos).
_DIRECTORY_DOMAINS = {
    'paginas-amarillas.cl', 'paginasamarillas.cl', 'amarillas.cl',
    'tucity.cl', 'guiacomercial.cl', 'cylex.cl', 'cylex.com',
    'yelp.com', 'foursquare.com', 'tripadvisor.com', 'tripadvisor.cl',
    'zomato.com', 'happycow.net', 'waze.com',
    'yapo.cl', 'chileautos.cl', 'portalinmobiliario.com',
    'ripley.cl', 'falabella.com', 'paris.cl', 'jumbo.cl',
    'mercadolibre.cl', 'mercadolibre.com',
    'infobel.com', 'infobel.cl',
    'empresasenlinea.cl', 'empresas.cl',
}

_ALLOWED_GENERIC_DOMAINS_SHARED = {
    'gmail.com', 'googlemail.com', 'hotmail.com', 'hotmail.cl',
    'outlook.com', 'outlook.cl', 'yahoo.com', 'yahoo.cl',
    'live.com', 'live.cl', 'icloud.com',
}
_BLOCKED_TLDS_SHARED = {
    '.es', '.mx', '.ar', '.pe', '.co', '.uk', '.de', '.fr',
    '.it', '.br', '.pt', '.us', '.ca', '.au', '.eu',
}
_SKIP_DOMAINS_SHARED = {
    'google.com', 'google.cl', 'bing.com', 'youtube.com', 'facebook.com',
    'instagram.com', 'twitter.com', 'linkedin.com', 'tiktok.com',
    'wikipedia.org', 'mercadopago.com', 'mercadolibre.com',
    'sentry.io', 'example.com', 'domain.com',
} | _DIRECTORY_DOMAINS

_SKIP_PREFIXES_SHARED = (
    'noreply', 'no-reply', 'donotreply', 'mailer', 'bounce',
    'webmaster', 'postmaster', 'abuse', 'spam', 'root',
    'admin', 'support', 'sales', 'press', 'media', 'legal', 'privacy',
)
_FILE_EXTENSIONS_SHARED = {
    '.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc',
    '.zip', '.css', '.js', '.svg', '.webp',
}


def _is_valid_business_email(e: str) -> bool:
    """
    Filtro unificado de emails para todos los métodos de prospección.
    Rechaza:
    - Dominios extranjeros (no .cl ni genéricos conocidos)
    - Directorios y plataformas (tucity, paginas amarillas, etc.)
    - Prefijos genéricos (noreply, admin, support, etc.)
    - Emails de prueba/gibberish: local == domain_name, dominio < 4 chars, patrón repetido
    - Extensiones de archivo confundidas con dominio
    """
    import re as _re
    e = e.lower().strip()
    parts = e.split('@')
    if len(parts) != 2:
        return False
    local, domain = parts

    # Extensión de archivo como dominio
    if any(domain.endswith(ext) for ext in _FILE_EXTENSIONS_SHARED):
        return False
    # Dominio en lista negra
    if domain in _SKIP_DOMAINS_SHARED:
        return False
    # Filtro geográfico: solo .cl o dominios genéricos conocidos
    is_cl      = domain.endswith('.cl')
    is_generic = domain in _ALLOWED_GENERIC_DOMAINS_SHARED
    if not is_cl and not is_generic:
        return False
    if any(domain.endswith(tld) for tld in _BLOCKED_TLDS_SHARED):
        return False
    # Prefijos genéricos
    if any(local.startswith(p) for p in _SKIP_PREFIXES_SHARED):
        return False
    # Largo mínimo local
    if len(local) < 3:
        return False

    # ── Filtros anti-gibberish ────────────────────────────────────────────────
    # Extraer nombre del dominio sin TLD (p.ej. "dasd" de "dasd.cl")
    domain_name = domain.rsplit('.', 2)[0] if domain.count('.') >= 2 else domain.split('.')[0]

    # 1) local == domain_name (dasd@dasd.cl, test@test.cl, demo@demo.cl)
    if local == domain_name:
        return False

    # 2) Nombre de dominio demasiado corto (< 4 chars: a.cl, ab.cl, abc.cl)
    if len(domain_name) < 4:
        return False

    # 3) Patrón repetido en local (aaaa, abababab, asdfasdf)
    if _re.match(r'^(.{1,4})\1{2,}$', local):   # ej: "asdf" repetido 3+ veces
        return False
    if len(set(local)) <= 2 and len(local) > 4:  # ej: "aaaaa", "ababab"
        return False

    # 4) Solo consonantes sin vocal → probable teclado random (dsd, xcvb)
    vowels = set('aeiouáéíóúü')
    if len(local) >= 5 and not any(c in vowels for c in local):
        return False

    return True


# ── Brave Web Search — scraping gratuito (2.000 queries/mes) ─────────────────

def _brave_get_leads(rubro: str, comuna: str, max_results: int = 20,
                     send_emails: bool = False) -> int:
    """
    Busca negocios usando Brave Search API (2.000 llamadas gratis/mes, sin tarjeta)
    + requests para visitar webs y extraer emails.

    Ventajas:
    - No necesita Chrome ni pantalla → compatible con PythonAnywhere
    - Busca en toda la web (sin restricciones)
    - country=CL fuerza resultados de Chile
    - 2.000 queries/mes gratis (plan Free en api.search.brave.com)

    Requiere en .env:
        BRAVE_SEARCH_API_KEY=BSA...

    Registro: https://api.search.brave.com → Sign up → Plan Free
    """
    import os
    import re
    import time
    import requests as req_lib
    from urllib.parse import urlparse

    api_key = os.getenv('BRAVE_SEARCH_API_KEY', '').strip()
    if not api_key:
        logger.error('[Brave] BRAVE_SEARCH_API_KEY no configurada en .env. Saltando.')
        return 0

    # ── Verificar cuántas queries Brave se usaron este mes ───────────────────
    monthly_limit = int(os.getenv('BRAVE_MONTHLY_LIMIT', '2000'))
    month = datetime.now().strftime('%Y-%m')
    conn_check = get_db()
    used_month = conn_check.execute(
        "SELECT COUNT(*) FROM et_outscraper_queries WHERE source='brave' AND created_at LIKE ?",
        (f'{month}%',)
    ).fetchone()[0]
    conn_check.close()
    if used_month >= monthly_limit:
        logger.warning(f'[Brave] Límite mensual alcanzado ({used_month}/{monthly_limit} queries). Saltando.')
        return 0

    EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.I)

    # Variantes de búsqueda para rotar resultados
    queries = [
        f'{rubro} {comuna} Santiago Chile contacto email',
        f'{rubro} {comuna} Santiago Chile correo',
        f'{rubro} en {comuna} Santiago de Chile email contacto',
        f'site:.cl {rubro} {comuna} email',
        f'{rubro} {comuna} Santiago Chile correo electronico',
    ]

    all_urls: list[str] = []
    queries_used = 0

    for q in queries:
        if used_month + queries_used >= monthly_limit:
            logger.info(f'[Brave] Límite mensual alcanzado durante búsqueda ({queries_used} queries esta llamada).')
            break

        params = {
            'q':       q,
            'count':   10,
            'country': 'CL',
            'lang':    'es',
        }
        try:
            r = req_lib.get(
                'https://api.search.brave.com/res/v1/web/search',
                headers={
                    'Accept':               'application/json',
                    'Accept-Encoding':      'gzip',
                    'X-Subscription-Token': api_key,
                },
                params=params,
                timeout=10
            )
            r.raise_for_status()
            items = r.json().get('web', {}).get('results', [])
            queries_used += 1
            for item in items:
                link = item.get('url', '')
                domain = urlparse(link).netloc.lower().replace('www.', '')
                if domain and domain not in _SKIP_DOMAINS_SHARED:
                    all_urls.append(link)
            logger.info(f'[Brave] Query "{q[:50]}..." → {len(items)} URLs')
        except Exception as exc:
            logger.error(f'[Brave] Error en query: {exc}')
            break

        time.sleep(0.3)

    # Deduplicar por dominio
    seen_domains: set = set()
    unique_urls: list[str] = []
    for url in all_urls:
        d = urlparse(url).netloc.lower().replace('www.', '')
        if d and d not in seen_domains and d not in _SKIP_DOMAINS_SHARED:
            seen_domains.add(d)
            unique_urls.append(url)

    logger.info(f'[Brave] {len(unique_urls)} URLs únicas para {rubro}/{comuna} ({queries_used} queries usadas)')

    # Registrar uso
    if queries_used > 0:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn_log = get_db()
        conn_log.execute(
            """INSERT INTO et_outscraper_queries
               (query, rubro, comuna, limit_req, total_found, with_email,
                credits_est, source, results_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (f'{rubro} {comuna} [Brave x{queries_used}]', rubro, comuna,
             queries_used, len(unique_urls), 0, 0, 'brave', '[]', now_str)
        )
        conn_log.commit()
        conn_log.close()

    # ── Visitar URLs y extraer emails ─────────────────────────────────────────
    conn  = get_db()
    tpl   = _get_template_for_rubro(rubro)
    saved = 0
    now   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Pre-cargar dominios ya scrapeados
    scraped_rows = conn.execute(
        '''SELECT LOWER(website) as w FROM et_contacts
           WHERE rubro LIKE ? AND LOWER(TRIM(comuna)) = ?
           AND website IS NOT NULL AND website != ""''',
        (f'%{rubro}%', comuna.lower().strip())
    ).fetchall()
    scraped_domains: set = set()
    for row in scraped_rows:
        try:
            d = urlparse(row['w']).netloc.lower().replace('www.', '')
            if d:
                scraped_domains.add(d)
        except Exception:
            pass

    page_session = req_lib.Session()
    page_session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    })

    for url in unique_urls[:max(max_results, 20)]:
        domain = urlparse(url).netloc.lower().replace('www.', '')
        if domain in scraped_domains:
            continue
        scraped_domains.add(domain)

        # Saltar directorios: incluir en unique_urls para deduplicar pero no extraer emails
        if domain in _DIRECTORY_DOMAINS:
            logger.debug(f'[Brave] Saltando directorio: {domain}')
            continue

        try:
            resp = page_session.get(url, timeout=8, allow_redirects=True)
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', resp.text, re.I)
            business_name = 'Negocio'
            if title_match:
                raw_title = title_match.group(1).strip()
                business_name = raw_title.split('|')[0].split('-')[0].strip()[:80]

            emails_found = [e for e in EMAIL_RE.findall(resp.text) if _is_valid_business_email(e)]

            if not emails_found:
                parsed = urlparse(url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                for path in ['/contacto', '/contact', '/contactanos', '/nosotros']:
                    try:
                        r2 = page_session.get(base + path, timeout=6)
                        emails_found = [e for e in EMAIL_RE.findall(r2.text) if _is_valid_business_email(e)]
                        if emails_found:
                            break
                    except Exception:
                        continue

            for email in emails_found[:2]:
                existing = conn.execute(
                    'SELECT id FROM et_contacts WHERE email = ?', (email,)
                ).fetchone()
                if existing:
                    continue

                followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                source_q    = f'brave:{rubro} {comuna}'

                if send_emails:
                    conn.execute(
                        '''INSERT INTO et_contacts
                           (business_name, email, website, rubro, ciudad, comuna,
                            source_query, created_at, campaign_status, fecha_envio,
                            proximo_seguimiento)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                        (business_name, email, url, rubro, 'Santiago', comuna,
                         source_q, now, 'enviado', now, followup_dt)
                    )
                    conn.commit()
                    subject = tpl['subject']
                    body    = tpl['body'].replace('{nombre}', business_name)
                    ok = _send_email(email, subject, body,
                                     rubro=rubro, contact_name=business_name)
                    if ok:
                        saved += 1
                        logger.info(f'[Brave] Enviado a {email} ({rubro}, {comuna})')
                    else:
                        conn.execute(
                            "UPDATE et_contacts SET campaign_status='no_enviado', "
                            "fecha_envio=NULL WHERE email=?", (email,)
                        )
                        conn.commit()
                else:
                    conn.execute(
                        '''INSERT INTO et_contacts
                           (business_name, email, website, rubro, ciudad, comuna,
                            source_query, created_at, campaign_status)
                           VALUES (?,?,?,?,?,?,?,?,?)''',
                        (business_name, email, url, rubro, 'Santiago', comuna,
                         source_q, now, 'no_enviado')
                    )
                    conn.commit()
                    saved += 1
                    logger.info(f'[Brave] Guardado (no_enviado): {email} ({rubro}, {comuna})')

        except Exception as exc:
            logger.debug(f'[Brave] Error visitando {url}: {exc}')
            continue

        time.sleep(1)

    conn.close()
    page_session.close()
    logger.info(f'[Brave] {rubro}/{comuna}: {saved} contactos nuevos guardados ({queries_used} queries Brave)')
    return saved


# ── Google Custom Search — scraping gratuito (100 queries/día) ───────────────

def _google_cse_get_leads(rubro: str, comuna: str, max_results: int = 20,
                           send_emails: bool = False) -> int:
    """
    Busca negocios usando Google Custom Search API (100 queries gratis/día)
    + requests para visitar webs y extraer emails.

    Ventajas vs Playwright:
    - No necesita Chrome ni pantalla → compatible con PythonAnywhere
    - No es bloqueado por Google (es la API oficial)
    - Cada query devuelve hasta 10 URLs; con 5 variantes → 50 URLs/rubro+comuna

    Límite: 100 queries gratuitas/día (configurable via GOOGLE_CSE_DAILY_LIMIT).
    Para más: $5 USD por 1.000 queries adicionales.

    Requiere en .env:
        GOOGLE_CSE_API_KEY=AIzaSy...
        GOOGLE_CSE_CX=xxxxxxxxx:yyyyyy
    """
    import os
    import re
    import time
    import requests as req_lib
    from urllib.parse import urlparse, urljoin, unquote

    api_key = os.getenv('GOOGLE_CSE_API_KEY', '').strip()
    cx      = os.getenv('GOOGLE_CSE_CX', '').strip()
    if not api_key or not cx:
        logger.error('[CSE] GOOGLE_CSE_API_KEY o GOOGLE_CSE_CX no configurados en .env. Saltando.')
        return 0

    # ── Verificar cuántas queries CSE se usaron hoy ───────────────────────────
    daily_limit = int(os.getenv('GOOGLE_CSE_DAILY_LIMIT', '100'))
    today = datetime.now().strftime('%Y-%m-%d')
    conn_check = get_db()
    used_today = conn_check.execute(
        "SELECT COUNT(*) FROM et_outscraper_queries WHERE source='cse' AND created_at LIKE ?",
        (f'{today}%',)
    ).fetchone()[0]
    conn_check.close()
    if used_today >= daily_limit:
        logger.warning(f'[CSE] Límite diario alcanzado ({used_today}/{daily_limit} queries). Saltando.')
        return 0

    EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.I)

    ALLOWED_GENERIC_DOMAINS = {
        'gmail.com', 'googlemail.com', 'hotmail.com', 'hotmail.cl',
        'outlook.com', 'outlook.cl', 'yahoo.com', 'yahoo.cl',
        'live.com', 'live.cl', 'icloud.com',
    }
    BLOCKED_TLDS = {
        '.es', '.mx', '.ar', '.pe', '.co', '.uk', '.de', '.fr',
        '.it', '.br', '.pt', '.us', '.ca', '.au', '.eu',
    }
    SKIP_DOMAINS = {
        'google.com', 'google.cl', 'youtube.com', 'facebook.com',
        'instagram.com', 'twitter.com', 'linkedin.com', 'tiktok.com',
        'wikipedia.org', 'mercadopago.com', 'mercadolibre.com',
        'sentry.io', 'example.com', 'domain.com',
    }
    SKIP_PREFIXES = (
        'noreply', 'no-reply', 'donotreply', 'mailer', 'bounce',
        'webmaster', 'postmaster', 'abuse', 'spam', 'root',
        'admin', 'support', 'sales', 'press', 'media', 'legal', 'privacy',
    )
    FILE_EXTENSIONS = {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc',
                       '.zip', '.css', '.js', '.svg', '.webp'}

    def _valid_email(e: str) -> bool:
        e = e.lower().strip()
        parts = e.split('@')
        if len(parts) != 2:
            return False
        local, domain = parts
        if any(domain.endswith(ext) for ext in FILE_EXTENSIONS):
            return False
        if domain in SKIP_DOMAINS:
            return False
        is_cl      = domain.endswith('.cl')
        is_generic = domain in ALLOWED_GENERIC_DOMAINS
        if not is_cl and not is_generic:
            return False
        if any(domain.endswith(tld) for tld in BLOCKED_TLDS):
            return False
        if any(local.startswith(p) for p in SKIP_PREFIXES):
            return False
        if len(local) < 3:
            return False
        return True

    def _fetch_emails_from_url(url: str, session: req_lib.Session) -> list[str]:
        """Visita una URL con requests y extrae emails válidos."""
        try:
            resp = session.get(url, timeout=8, allow_redirects=True)
            emails = [e for e in EMAIL_RE.findall(resp.text) if _valid_email(e)]
            if emails:
                return emails

            # Intentar /contacto si la página principal no tiene email
            parsed = urlparse(url)
            base = f"{parsed.scheme}://{parsed.netloc}"
            for path in ['/contacto', '/contact', '/contactanos', '/nosotros']:
                try:
                    r2 = session.get(base + path, timeout=6)
                    emails2 = [e for e in EMAIL_RE.findall(r2.text) if _valid_email(e)]
                    if emails2:
                        return emails2
                except Exception:
                    continue
        except Exception as exc:
            logger.debug(f'[CSE] Error fetching {url}: {exc}')
        return []

    # ── Variantes de query para rotar y no repetir resultados ─────────────────
    queries = [
        f'{rubro} {comuna} Santiago Chile contacto email',
        f'{rubro} {comuna} Santiago Chile correo',
        f'site:.cl {rubro} {comuna} email contacto',
        f'{rubro} en {comuna} Santiago de Chile correo electronico',
        f'site:.cl {rubro} {comuna} contacto',
    ]

    session = req_lib.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    })

    all_urls: list[str] = []
    queries_used = 0

    for q in queries:
        if used_today + queries_used >= daily_limit:
            logger.info(f'[CSE] Límite diario alcanzado durante búsqueda ({queries_used} queries esta llamada).')
            break

        params = {
            'key': api_key,
            'cx':  cx,
            'q':   q,
            'num': 10,
            'gl':  'cl',
            'hl':  'es',
        }
        try:
            r = req_lib.get('https://www.googleapis.com/customsearch/v1',
                            params=params, timeout=10)
            r.raise_for_status()
            items = r.json().get('items', [])
            queries_used += 1
            for item in items:
                link = item.get('link', '')
                domain = urlparse(link).netloc.lower().replace('www.', '')
                if domain and domain not in SKIP_DOMAINS:
                    all_urls.append(link)
            logger.info(f'[CSE] Query "{q[:50]}..." → {len(items)} URLs')
        except Exception as exc:
            logger.error(f'[CSE] Error en query CSE: {exc}')
            break

        time.sleep(0.5)   # respetar rate limit de la API

    # Deduplicar URLs por dominio
    seen_domains: set = set()
    unique_urls: list[str] = []
    for url in all_urls:
        d = urlparse(url).netloc.lower().replace('www.', '')
        if d and d not in seen_domains and d not in SKIP_DOMAINS:
            seen_domains.add(d)
            unique_urls.append(url)

    logger.info(f'[CSE] {len(unique_urls)} URLs únicas para {rubro}/{comuna} ({queries_used} queries usadas)')

    # Registrar uso para tracking
    if queries_used > 0:
        now_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        conn_log = get_db()
        conn_log.execute(
            """INSERT INTO et_outscraper_queries
               (query, rubro, comuna, limit_req, total_found, with_email,
                credits_est, source, results_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (f'{rubro} {comuna} [CSE x{queries_used}]', rubro, comuna,
             queries_used, len(unique_urls), 0, 0, 'cse', '[]', now_str)
        )
        conn_log.commit()
        conn_log.close()

    # ── Visitar URLs y extraer emails ─────────────────────────────────────────
    conn  = get_db()
    tpl   = _get_template_for_rubro(rubro)
    saved = 0
    now   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    # Pre-cargar dominios ya scrapeados para este rubro+comuna
    scraped_rows = conn.execute(
        '''SELECT LOWER(website) as w FROM et_contacts
           WHERE rubro LIKE ? AND LOWER(TRIM(comuna)) = ?
           AND website IS NOT NULL AND website != ""''',
        (f'%{rubro}%', comuna.lower().strip())
    ).fetchall()
    scraped_domains: set = set()
    for row in scraped_rows:
        try:
            d = urlparse(row['w']).netloc.lower().replace('www.', '')
            if d:
                scraped_domains.add(d)
        except Exception:
            pass

    for url in unique_urls[:max(max_results, 20)]:
        domain = urlparse(url).netloc.lower().replace('www.', '')
        if domain in scraped_domains:
            continue
        scraped_domains.add(domain)

        try:
            title_resp = req_lib.get(url, timeout=8, allow_redirects=True)
            # Extraer título de la página como nombre del negocio
            title_match = re.search(r'<title[^>]*>([^<]+)</title>', title_resp.text, re.I)
            business_name = 'Negocio'
            if title_match:
                raw_title = title_match.group(1).strip()
                business_name = raw_title.split('|')[0].split('-')[0].strip()[:80]

            emails_found = [e for e in EMAIL_RE.findall(title_resp.text) if _valid_email(e)]

            if not emails_found:
                # Intentar /contacto
                parsed = urlparse(url)
                base = f"{parsed.scheme}://{parsed.netloc}"
                for path in ['/contacto', '/contact', '/contactanos', '/nosotros']:
                    try:
                        r2 = session.get(base + path, timeout=6)
                        emails_found = [e for e in EMAIL_RE.findall(r2.text) if _valid_email(e)]
                        if emails_found:
                            break
                    except Exception:
                        continue

            for email in emails_found[:2]:
                existing = conn.execute(
                    'SELECT id FROM et_contacts WHERE email = ?', (email,)
                ).fetchone()
                if existing:
                    logger.debug(f'[CSE] Saltado (ya existe): {email}')
                    continue

                followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
                source_q = f'cse:{rubro} {comuna}'

                if send_emails:
                    conn.execute(
                        '''INSERT INTO et_contacts
                           (business_name, email, website, rubro, ciudad, comuna,
                            source_query, created_at, campaign_status, fecha_envio,
                            proximo_seguimiento)
                           VALUES (?,?,?,?,?,?,?,?,?,?,?)''',
                        (business_name, email, url, rubro, 'Santiago', comuna,
                         source_q, now, 'enviado', now, followup_dt)
                    )
                    conn.commit()
                    subject = tpl['subject']
                    body    = tpl['body'].replace('{nombre}', business_name)
                    ok = _send_email(email, subject, body,
                                     rubro=rubro, contact_name=business_name)
                    if ok:
                        saved += 1
                        logger.info(f'[CSE] Enviado a {email} ({rubro}, {comuna})')
                    else:
                        conn.execute(
                            "UPDATE et_contacts SET campaign_status='no_enviado', "
                            "fecha_envio=NULL WHERE email=?", (email,)
                        )
                        conn.commit()
                else:
                    conn.execute(
                        '''INSERT INTO et_contacts
                           (business_name, email, website, rubro, ciudad, comuna,
                            source_query, created_at, campaign_status)
                           VALUES (?,?,?,?,?,?,?,?,?)''',
                        (business_name, email, url, rubro, 'Santiago', comuna,
                         source_q, now, 'no_enviado')
                    )
                    conn.commit()
                    saved += 1
                    logger.info(f'[CSE] Guardado (no_enviado): {email} ({rubro}, {comuna})')

        except Exception as exc:
            logger.debug(f'[CSE] Error visitando {url}: {exc}')
            continue

        time.sleep(1)  # pausa entre visitas

    conn.close()
    session.close()
    logger.info(f'[CSE] {rubro}/{comuna}: {saved} contactos nuevos guardados ({queries_used} queries CSE)')
    return saved


# ── Budget Outscraper ─────────────────────────────────────────────────────────

def _get_outscraper_budget_status() -> dict:
    """
    Retorna el estado del presupuesto mensual de Outscraper.
    Suma créditos estimados del mes en curso desde et_outscraper_queries.
    """
    from database import get_config
    now   = datetime.now()
    month = now.strftime('%Y-%m')

    budget_usd      = float(get_config('outscraper_monthly_budget_usd') or '10')
    credits_per_usd = float(get_config('outscraper_credits_per_usd')    or '500')

    conn = get_db()
    row  = conn.execute(
        "SELECT COALESCE(SUM(credits_est), 0) as total FROM et_outscraper_queries "
        "WHERE created_at LIKE ?",
        (f'{month}%',)
    ).fetchone()
    conn.close()

    credits_used = row['total'] if row else 0
    usd_used     = round(credits_used / credits_per_usd, 4)
    usd_left     = max(0.0, budget_usd - usd_used)
    pct          = min(100, round(usd_used / budget_usd * 100, 1)) if budget_usd else 0
    blocked      = usd_used >= budget_usd

    return {
        'month':          month,
        'budget_usd':     budget_usd,
        'usd_used':       usd_used,
        'usd_left':       usd_left,
        'pct':            pct,
        'blocked':        blocked,
        'credits_used':   int(credits_used),
        'credits_per_usd': int(credits_per_usd),
    }


def _log_outscraper_usage(query: str, rubro: str, comuna: str,
                           n_places: int, n_with_email: int, source: str = 'auto') -> None:
    """Registra uso en et_outscraper_queries para el tracking de presupuesto."""
    import json as _json
    credits_est = n_places * 3 + n_with_email * 2
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    try:
        conn = get_db()
        conn.execute(
            """INSERT INTO et_outscraper_queries
               (query, rubro, comuna, limit_req, total_found, with_email, credits_est, source, results_json, created_at)
               VALUES (?,?,?,?,?,?,?,?,?,?)""",
            (query, rubro, comuna, n_places, n_places, n_with_email,
             credits_est, source, _json.dumps([]), now)
        )
        conn.commit()
        conn.close()
    except Exception as e:
        logger.warning(f'[BudgetLog] No se pudo registrar uso: {e}')


def _outscraper_get_leads(rubro: str, comuna: str, max_results: int = 20,
                           send_emails: bool = False) -> int:
    """
    Busca negocios en Google Maps via Outscraper API y guarda contactos nuevos.
    Reemplaza _scrape_rubro_comuna (Playwright) que era bloqueado por Google.

    - send_emails=False → guarda como 'no_enviado' para que email_daily lo envíe a las 11:00.
    - send_emails=True  → guarda como 'enviado' y manda el email inmediatamente (Paso 2).
    - Deduplica por email contra et_contacts antes de insertar.
    - max_results se limita a OUTSCRAPER_DAILY_LIMIT por llamada para controlar créditos.

    Budget ref: plan ~$9/mes → ~3 000 créditos → ~600 places/mes con enrichment (5 cr/place).
    Con OUTSCRAPER_DAILY_LIMIT=20 (default) → ~600 places/mes = presupuesto justo.
    """
    import os
    import re

    api_key = os.getenv('OUTSCRAPER_API_KEY', '').strip()
    if not api_key:
        logger.error('[Outscraper] OUTSCRAPER_API_KEY no configurada en .env. Saltando scraping.')
        return 0

    # ── Verificar límite gratuito mensual (sin gasto extra) ─────────────────
    free_limit  = int(os.getenv('OUTSCRAPER_FREE_MONTHLY_LIMIT', '25'))
    month_start = datetime.now().strftime('%Y-%m-01')
    conn_free   = get_db()
    used_month  = conn_free.execute(
        "SELECT COUNT(*) FROM et_outscraper_queries WHERE created_at >= ?",
        (month_start,)
    ).fetchone()[0]
    conn_free.close()
    if used_month >= free_limit:
        logger.warning(
            f'[Outscraper] Límite gratuito mensual alcanzado '
            f'({used_month}/{free_limit} queries). Saltando hasta el mes siguiente.'
        )
        return 0

    # Límite configurable por llamada para no agotar créditos (env OUTSCRAPER_DAILY_LIMIT)
    cap = int(os.getenv('OUTSCRAPER_DAILY_LIMIT', '20'))
    max_results = min(max_results, cap)

    query = f'{rubro} {comuna} Santiago Chile'
    logger.info(f'[Outscraper] Buscando: "{query}" (límite {max_results} results)')

    try:
        from outscraper import ApiClient
        client  = ApiClient(api_key=api_key)
        results = client.google_maps_search(
            [query],
            limit=max_results,
            enrichment=['domains_service'],
            language='es',
            region='CL',
        )
    except Exception as exc:
        logger.error(f'[Outscraper] Error en API call {rubro}/{comuna}: {exc}')
        return 0

    if not results or not isinstance(results, list):
        logger.info(f'[Outscraper] Respuesta vacía para "{query}"')
        return 0

    # Outscraper devuelve [[place, place, ...]] — una sublista por query enviada
    places = results[0] if isinstance(results[0], list) else results
    if not places:
        logger.info(f'[Outscraper] 0 lugares encontrados para "{query}"')
        return 0

    logger.info(f'[Outscraper] {len(places)} lugares recibidos para "{query}"')

    # ── Registrar uso para presupuesto (antes de filtrar) ────────────────────
    n_with_email_raw = sum(1 for p in places if isinstance(p, dict) and any(p.get(f'email_{i}') for i in range(1,6)))
    _log_outscraper_usage(query, rubro, comuna, len(places), n_with_email_raw, source='auto')

    # Regex permisiva; el filtro fino se aplica debajo
    EMAIL_RE = re.compile(
        r'^[a-zA-Z0-9._%+\-]{3,}@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}$'
    )
    SKIP_PREFIXES = (
        'noreply', 'no-reply', 'donotreply', 'mailer-daemon',
        'bounce', 'webmaster', 'postmaster', 'abuse', 'spam',
        'root', 'admin@', 'support@', 'sales@', 'press@', 'media@',
        'privacy@', 'legal@',
    )
    SKIP_DOMAINS = {
        'sentry.io', 'example.com', 'domain.com', 'test.com',
        'mercadopago.com', 'mercadolibre.com',
        'facebook.com', 'instagram.com', 'twitter.com',
        'youtube.com', 'google.com', 'google.cl',
    }

    def _valid_email(e: str) -> bool:
        e = e.lower().strip()
        if not EMAIL_RE.match(e):
            return False
        local, domain = e.rsplit('@', 1)
        if domain in SKIP_DOMAINS:
            return False
        if any(local.startswith(p.rstrip('@')) for p in SKIP_PREFIXES):
            return False
        return True

    conn   = get_db()
    saved  = 0
    tpl    = _get_template_for_rubro(rubro)
    now    = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    for place in places:
        if not isinstance(place, dict):
            continue

        business_name = (place.get('name') or '').strip()[:80]
        if not business_name:
            continue

        # ── Recopilar candidatos de email ─────────────────────────────────
        # Outscraper (google_maps_search + domains_service) devuelve los emails
        # como campos planos: email_1, email_2, email_3, ... en el dict del lugar.
        raw: list[str] = []

        # 1) Campos planos email_1..email_5 (formato real de la API)
        for i in range(1, 6):
            val = place.get(f'email_{i}') or ''
            if val:
                raw.extend(str(val).split(','))

        # 2) Fallback: campos alternativos que algunas versiones usan
        for field in ('email', 'emails', 'contact_email'):
            val = place.get(field) or ''
            if val:
                raw.extend(str(val).split(','))

        # 3) emails_from_website (formato enrichment legacy)
        enrich = place.get('emails_from_website') or []
        if isinstance(enrich, list):
            for item in enrich:
                v = item.get('value', '') if isinstance(item, dict) else str(item)
                if v:
                    raw.extend(v.split(','))

        candidates = [e.strip().lower() for e in raw if _valid_email(e.strip())]
        if not candidates:
            continue

        phone   = (place.get('phone')   or '')[:30].strip()
        website = (place.get('website') or place.get('site') or '')[:255].strip()
        source  = f'outscraper:{query}'

        for email in candidates[:2]:   # máx 2 emails por negocio
            existing = conn.execute(
                'SELECT id FROM et_contacts WHERE email = ?', (email,)
            ).fetchone()
            if existing:
                logger.debug(f'[Outscraper] Saltado (ya existe): {email}')
                continue

            followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')

            if send_emails:
                conn.execute(
                    '''INSERT INTO et_contacts
                       (business_name, email, phone, website, rubro, ciudad, comuna,
                        source_query, created_at, campaign_status, fecha_envio,
                        proximo_seguimiento)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (business_name, email, phone, website, rubro, 'Santiago', comuna,
                     source, now, 'enviado', now, followup_dt),
                )
                conn.commit()
                subject = tpl['subject']
                body    = tpl['body'].replace('{nombre}', business_name)
                ok = _send_email(email, subject, body,
                                 rubro=rubro, contact_name=business_name)
                if ok:
                    saved += 1
                    logger.info(f'[Outscraper] Enviado a {email} ({rubro}, {comuna})')
                else:
                    conn.execute(
                        "UPDATE et_contacts SET campaign_status='no_enviado', "
                        "fecha_envio=NULL WHERE email=?",
                        (email,),
                    )
                    conn.commit()
            else:
                conn.execute(
                    '''INSERT INTO et_contacts
                       (business_name, email, phone, website, rubro, ciudad, comuna,
                        source_query, created_at, campaign_status)
                       VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (business_name, email, phone, website, rubro, 'Santiago', comuna,
                     source, now, 'no_enviado'),
                )
                conn.commit()
                saved += 1
                logger.info(f'[Outscraper] Guardado (no_enviado): {email} ({rubro}, {comuna})')

    conn.close()
    logger.info(f'[Outscraper] {rubro}/{comuna}: {saved} contactos nuevos guardados')
    return saved


# ── Reglas de enrutamiento por rubro + zona ──────────────────────────────────
# Cada método tiene su conjunto exclusivo de rubros y comunas.
# Si un par rubro+comuna no cae en ninguna regla → Google CSE (comodín).

# Outscraper — rubros premium zona oriente (alta conversión, vale el costo)
_OUTSCRAPER_RUBROS = {
    'tienda de muebles', 'tienda muebles',
    'oftalmología', 'oftalmologia',
    'pizzería', 'pizzeria',
    'clínica dental', 'clinica dental', 'clínicas dentales', 'clinicas dentales',
    'clínica de belleza', 'clinica de belleza', 'clínica belleza', 'clinica belleza',
}
_OUTSCRAPER_COMUNAS = {
    'la reina', 'providencia', 'las condes', 'vitacura', 'santiago centro',
}

# Brave — rubros automotriz/servicio zona norte (excluye Conchalí, Cerro Navia, Renca)
_BRAVE_RUBROS = {
    'frenos', 'lubricentro', 'spa', 'ferretería', 'ferreteria',
}
_BRAVE_COMUNAS = {
    'independencia', 'huechuraba', 'lo barnechea', 'colina', 'lampa',
    'quilicura', 'recoleta', 'lo prado', 'quinta normal', 'til til',
    'pudahuel', 'estación central', 'estacion central',
}
# Comunas norte excluidas explícitamente (no van a Brave aunque el rubro coincida)
_BRAVE_COMUNAS_EXCLUIDAS = {'conchalí', 'conchali', 'cerro navia', 'renca'}

# Serper.dev — resultados reales de Google, 2.500 queries gratis/mes (comodín)


def _serper_get_leads(rubro: str, comuna: str, max_results: int = 20,
                      send_emails: bool = False) -> int:
    """
    Busca negocios usando Serper.dev (resultados reales de Google).
    2.500 queries gratuitas/mes — sin restricción de sitios, filtro Chile nativo.

    API: POST https://google.serper.dev/search
    Headers: X-API-KEY, Content-Type: application/json
    Body: {"q": "...", "gl": "cl", "hl": "es", "num": 10}

    Requiere en .env:
        SERPER_API_KEY=...
    """
    import os
    import re
    import time
    import requests as req_lib
    from urllib.parse import urlparse

    api_key = os.getenv('SERPER_API_KEY', '').strip()
    if not api_key:
        logger.error('[Serper] SERPER_API_KEY no configurada en .env. Saltando.')
        return 0

    monthly_limit = int(os.getenv('SERPER_MONTHLY_LIMIT', '2500'))
    month_start   = datetime.now().strftime('%Y-%m-01')
    conn_check    = get_db()
    used_month    = conn_check.execute(
        "SELECT COUNT(*) FROM et_outscraper_queries WHERE source='serper' AND created_at >= ?",
        (month_start,)
    ).fetchone()[0]
    conn_check.close()
    if used_month >= monthly_limit:
        logger.warning(f'[Serper] Límite mensual alcanzado ({used_month}/{monthly_limit}). Saltando.')
        return 0

    EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+\-]+@[a-zA-Z0-9.\-]+\.[a-zA-Z]{2,}', re.I)

    ALLOWED_GENERIC_DOMAINS = {
        'gmail.com', 'googlemail.com', 'hotmail.com', 'hotmail.cl',
        'outlook.com', 'outlook.cl', 'yahoo.com', 'yahoo.cl',
        'live.com', 'live.cl', 'icloud.com',
    }
    BLOCKED_TLDS  = {'.es', '.mx', '.ar', '.pe', '.co', '.uk', '.de', '.fr',
                     '.it', '.br', '.pt', '.us', '.ca', '.au', '.eu'}
    SKIP_DOMAINS  = {
        'google.com', 'google.cl', 'youtube.com', 'facebook.com',
        'instagram.com', 'twitter.com', 'linkedin.com', 'tiktok.com',
        'wikipedia.org', 'mercadopago.com', 'mercadolibre.com',
        'sentry.io', 'example.com', 'domain.com',
    } | _DIRECTORY_DOMAINS
    SKIP_PREFIXES = (
        'noreply', 'no-reply', 'donotreply', 'mailer', 'bounce',
        'webmaster', 'postmaster', 'abuse', 'spam', 'root',
        'admin', 'support', 'sales', 'press', 'media', 'legal', 'privacy',
    )
    FILE_EXT = {'.png', '.jpg', '.jpeg', '.gif', '.pdf', '.doc',
                '.zip', '.css', '.js', '.svg', '.webp'}

    def _valid_email(e: str) -> bool:
        e = e.lower().strip()
        parts = e.split('@')
        if len(parts) != 2:
            return False
        local, domain = parts
        if any(domain.endswith(x) for x in FILE_EXT):
            return False
        if domain in SKIP_DOMAINS:
            return False
        is_cl      = domain.endswith('.cl')
        is_generic = domain in ALLOWED_GENERIC_DOMAINS
        if not is_cl and not is_generic:
            return False
        if any(domain.endswith(t) for t in BLOCKED_TLDS):
            return False
        if any(local.startswith(p) for p in SKIP_PREFIXES):
            return False
        if len(local) < 3:
            return False
        return _is_valid_business_email(e)

    def _fetch_emails(url: str, session: req_lib.Session) -> list[str]:
        try:
            resp   = session.get(url, timeout=8, allow_redirects=True)
            emails = [e for e in EMAIL_RE.findall(resp.text) if _valid_email(e)]
            if emails:
                return emails
            parsed = urlparse(url)
            base   = f"{parsed.scheme}://{parsed.netloc}"
            for path in ['/contacto', '/contact', '/contactanos', '/nosotros']:
                try:
                    r2 = session.get(base + path, timeout=6)
                    e2 = [e for e in EMAIL_RE.findall(r2.text) if _valid_email(e)]
                    if e2:
                        return e2
                except Exception:
                    continue
        except Exception as exc:
            logger.debug(f'[Serper] Error fetching {url}: {exc}')
        return []

    queries = [
        f'{rubro} {comuna} Santiago Chile email contacto',
        f'{rubro} {comuna} Santiago Chile correo',
        f'{rubro} en {comuna} Santiago de Chile correo electronico',
        f'{rubro} {comuna} Chile contacto web email',
        f'{rubro} pequeña empresa {comuna} Santiago contacto',
    ]

    session = req_lib.Session()
    session.headers.update({
        'User-Agent': (
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
            'AppleWebKit/537.36 (KHTML, like Gecko) '
            'Chrome/124.0.0.0 Safari/537.36'
        )
    })

    all_urls: list[str] = []
    queries_used = 0

    for q in queries:
        if used_month + queries_used >= monthly_limit:
            break

        payload = {'q': q, 'gl': 'cl', 'hl': 'es', 'num': 10}
        headers = {'X-API-KEY': api_key, 'Content-Type': 'application/json'}
        try:
            r = req_lib.post('https://google.serper.dev/search',
                             json=payload, headers=headers, timeout=10)
            r.raise_for_status()
            items = r.json().get('organic', [])
            queries_used += 1

            # Registrar uso en BD
            conn_log = get_db()
            conn_log.execute(
                "INSERT INTO et_outscraper_queries (query, rubro, comuna, source, created_at) VALUES (?,?,?,?,?)",
                (q, rubro, comuna, 'serper', datetime.now().strftime('%Y-%m-%d %H:%M:%S'))
            )
            conn_log.commit()
            conn_log.close()

            for item in items:
                link   = item.get('link', '')
                domain = urlparse(link).netloc.lower().replace('www.', '')
                if domain and domain not in SKIP_DOMAINS:
                    all_urls.append(link)
            logger.info(f'[Serper] Query "{q[:55]}..." → {len(items)} URLs')
            time.sleep(0.3)
        except Exception as exc:
            logger.warning(f'[Serper] Error en query: {exc}')
            break

    # ── Visitar URLs y extraer emails ─────────────────────────────────────────
    seen_domains: set[str] = set()
    saved = 0
    now   = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn  = get_db()

    try:
        tpl_row = conn.execute(
            "SELECT * FROM et_rubro_templates WHERE LOWER(rubro)=? LIMIT 1",
            (rubro.lower().strip(),)
        ).fetchone()
        tpl = dict(tpl_row) if tpl_row else None
    except Exception:
        tpl = None

    for url in all_urls:
        if saved >= max_results:
            break
        domain = urlparse(url).netloc.lower().replace('www.', '')
        if domain in seen_domains or domain in SKIP_DOMAINS:
            continue
        seen_domains.add(domain)

        emails = _fetch_emails(url, session)
        for email in emails:
            if saved >= max_results:
                break
            source_q = f'serper:{rubro} {comuna}'
            existing = conn.execute(
                "SELECT id FROM et_contacts WHERE LOWER(email)=?",
                (email.lower(),)
            ).fetchone()
            if existing:
                logger.debug(f'[Serper] Saltado (ya existe): {email}')
                continue

            followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
            business_name = domain.replace('.cl', '').replace('-', ' ').replace('.', ' ').title()

            if send_emails and tpl:
                conn.execute(
                    '''INSERT INTO et_contacts
                       (business_name, email, phone, website, rubro, ciudad, comuna,
                        source_query, created_at, campaign_status, fecha_envio, proximo_seguimiento)
                       VALUES (?,?,?,?,?,?,?,?,?,?,?,?)''',
                    (business_name, email, '', url, rubro, 'Santiago', comuna,
                     source_q, now, 'enviado', now, followup_dt),
                )
                conn.commit()
                subject = tpl['subject']
                body    = tpl['body'].replace('{nombre}', business_name)
                ok = _send_email(email, subject, body, rubro=rubro, contact_name=business_name)
                if ok:
                    saved += 1
                    logger.info(f'[Serper] Enviado a {email} ({rubro}, {comuna})')
                else:
                    conn.execute(
                        "UPDATE et_contacts SET campaign_status='no_enviado', fecha_envio=NULL WHERE email=?",
                        (email,)
                    )
                    conn.commit()
            else:
                conn.execute(
                    '''INSERT INTO et_contacts
                       (business_name, email, phone, website, rubro, ciudad, comuna,
                        source_query, created_at, campaign_status)
                       VALUES (?,?,?,?,?,?,?,?,?,?)''',
                    (business_name, email, '', url, rubro, 'Santiago', comuna,
                     source_q, now, 'no_enviado'),
                )
                conn.commit()
                saved += 1
                logger.info(f'[Serper] Guardado: {email} ({rubro}, {comuna})')

    conn.close()
    logger.info(f'[Serper] Completado: {saved} leads guardados para {rubro}/{comuna}')
    return saved


def _get_leads(rubro: str, comuna: str, max_results: int = 20,
               send_emails: bool = False) -> int:
    """
    Router de prospección basado en reglas rubro+zona.

    Regla 1 — Outscraper (pago, alta calidad):
        rubros: tienda de muebles, oftalmología, pizzería, clínica dental, clínica de belleza
        comunas: La Reina, Providencia, Las Condes, Vitacura, Santiago Centro

    Regla 2 — Brave Search (gratis, 2.000/mes):
        rubros: frenos, lubricentro, spa, ferretería
        comunas: zona norte — Independencia, Huechuraba, Lo Barnechea, Colina, Lampa, etc.
        excluye: Conchalí, Cerro Navia, Renca

    Regla 3 — Serper.dev (gratis, 2.500/mes) — comodín:
        todo lo que no caiga en Regla 1 ni Regla 2
        resultados reales de Google filtrados a Chile (gl=cl)

    Fallback: si la API asignada no está configurada, baja al siguiente método disponible.
    """
    import os

    rk = rubro.lower().strip()
    ck = comuna.lower().strip()

    has_outscraper = bool(os.getenv('OUTSCRAPER_API_KEY', '').strip())
    has_brave      = bool(os.getenv('BRAVE_SEARCH_API_KEY', '').strip())
    has_serper     = bool(os.getenv('SERPER_API_KEY', '').strip())
    has_cse        = bool(os.getenv('GOOGLE_CSE_API_KEY', '').strip() and
                          os.getenv('GOOGLE_CSE_CX', '').strip())

    # ── Regla 1: Outscraper — rubros premium zona oriente ────────────────────
    if rk in _OUTSCRAPER_RUBROS and ck in _OUTSCRAPER_COMUNAS:
        if has_outscraper:
            logger.info(f'[Leads] OUTSCRAPER (zona oriente) → {rubro}/{comuna}')
            return _outscraper_get_leads(rubro, comuna, max_results, send_emails)
        else:
            logger.warning(f'[Leads] Regla Outscraper sin API key → fallback para {rubro}/{comuna}')

    # ── Regla 2: Brave — rubros automotriz/servicio zona norte ───────────────
    if rk in _BRAVE_RUBROS and ck in _BRAVE_COMUNAS and ck not in _BRAVE_COMUNAS_EXCLUIDAS:
        if has_brave:
            logger.info(f'[Leads] BRAVE (zona norte) → {rubro}/{comuna}')
            return _brave_get_leads(rubro, comuna, max_results, send_emails)
        else:
            logger.warning(f'[Leads] Regla Brave sin API key → fallback para {rubro}/{comuna}')

    # ── Regla 3: Serper.dev — comodín para todo lo demás ────────────────────
    if has_serper:
        logger.info(f'[Leads] SERPER (comodín Google) → {rubro}/{comuna}')
        return _serper_get_leads(rubro, comuna, max_results, send_emails)

    # ── Fallback: Google CSE si está configurado ─────────────────────────────
    if has_cse:
        logger.info(f'[Leads] Fallback GOOGLE CSE → {rubro}/{comuna}')
        return _google_cse_get_leads(rubro, comuna, max_results, send_emails)

    # ── Fallback final: cualquier API disponible ─────────────────────────────
    if has_brave:
        logger.info(f'[Leads] Fallback BRAVE → {rubro}/{comuna}')
        return _brave_get_leads(rubro, comuna, max_results, send_emails)
    if has_outscraper:
        logger.info(f'[Leads] Fallback OUTSCRAPER → {rubro}/{comuna}')
        return _outscraper_get_leads(rubro, comuna, max_results, send_emails)

    logger.warning(
        f'[Leads] Sin método de prospección disponible para {rubro}/{comuna}. '
        'Configura SERPER_API_KEY, BRAVE_SEARCH_API_KEY o OUTSCRAPER_API_KEY en .env'
    )
    return 0


def _get_intel_targets(target_pendiente: int = 100) -> list[tuple[str, str, int]]:
    """
    Fix 1+3: Rubros desde et_rubro_templates + comunas solo de COMUNAS_SANTIAGO.
    Consulta la DB y devuelve lista de (rubro, comuna, max_items) priorizados:
    1. Rubros de et_rubro_templates sin contactos en et_contacts → prioridad alta
    2. Rubros con pocos contactos pendientes en et_contacts (< 10) → prioridad media
    3. Comunas con mejor tasa de respuesta, validadas contra COMUNAS_SANTIAGO
    """
    import secrets

    # Fix 1: fuente de verdad = et_rubro_templates (no hardcoded ni rubros_config)
    active_rubros = _get_active_rubros()
    n_rubros      = max(len(active_rubros), 1)

    conn = get_db()

    # Contactos et_contacts por rubro (email prospecting)
    email_stats = conn.execute(
        """SELECT LOWER(TRIM(rubro)) as r,
                  COUNT(*) as total,
                  COUNT(CASE WHEN campaign_status IN ('pendiente','no_enviado') THEN 1 END) as pendientes
           FROM et_contacts
           WHERE rubro IS NOT NULL AND rubro != ''
           GROUP BY LOWER(TRIM(rubro))"""
    ).fetchall()
    email_total_map     = {r['r']: r['total']     for r in email_stats}
    email_pendiente_map = {r['r']: r['pendientes'] for r in email_stats}

    # Fix 3: comunas con mejor tasa — SOLO las que están en COMUNAS_SANTIAGO
    top_comunas_rows = conn.execute('''
        SELECT l.comuna,
               COUNT(DISTINCT CASE WHEN ls.status='interesado' THEN l.id END) AS interesados
        FROM leads l
        LEFT JOIN lead_status ls ON l.id = ls.lead_id
        WHERE l.comuna IS NOT NULL AND l.comuna != ''
        GROUP BY l.comuna
        ORDER BY interesados DESC
        LIMIT 20
    ''').fetchall()
    conn.close()

    # Filtrar a solo comunas válidas del listado oficial
    mejores_comunas = [
        r['comuna'] for r in top_comunas_rows
        if r['comuna'].lower().strip() in _COMUNAS_LOWER
    ]
    if not mejores_comunas:
        mejores_comunas = COMUNAS_SANTIAGO[:8]

    targets = []

    # Prioridad 1: rubros activos sin ningún contacto en et_contacts → urgente
    for rubro in active_rubros:
        rk = rubro.lower().strip()
        if email_total_map.get(rk, 0) == 0:
            targets.append((rubro, secrets.choice(mejores_comunas[:6]), 15))

    # Prioridad 2: rubros con pocos pendientes → completar stock
    for rubro in active_rubros:
        rk = rubro.lower().strip()
        if email_pendiente_map.get(rk, 0) < 10:
            comunas = _get_least_prospected_comunas(rubro, n=2)
            for comuna in comunas:
                targets.append((rubro, comuna, max(8, target_pendiente // n_rubros)))

    # Evitar duplicados rubro+comuna y garantizar comunas válidas
    seen   = set()
    unique = []
    for rubro, comuna, n in targets:
        # Fix 3: descartar cualquier comuna que no esté en COMUNAS_SANTIAGO
        if comuna.lower().strip() not in _COMUNAS_LOWER:
            continue
        k = (rubro.lower(), comuna.lower())
        if k not in seen:
            seen.add(k)
            unique.append((rubro, comuna, n))

    return unique


def run_intel_scraping():
    """
    Job de relleno del pool — corre a las 08:00 AM y también se dispara
    automáticamente cuando el pool cae por debajo de REFILL_THRESHOLD.

    Lógica:
    - Verifica cuántos leads hay en estado no_enviado en et_contacts.
    - Si el pool ya tiene ≥ POOL_TARGET (1000): no hace nada.
    - Si hay déficit: busca leads via Brave → Google CSE → Outscraper
      (según reglas rubro+zona) hasta cubrir el déficit o agotar los
      límites de API del día.
    - Nunca inserta emails duplicados (validado contra et_contacts.email).
    """
    from database import job_run

    POOL_TARGET = 1000  # tamaño objetivo del pool no_enviado

    # ── Verificar pool actual ────────────────────────────────────────────────
    conn_check = get_db()
    current_pool = conn_check.execute(
        "SELECT COUNT(*) FROM et_contacts WHERE campaign_status IN ('no_enviado','pendiente')"
    ).fetchone()[0]
    conn_check.close()

    if current_pool >= POOL_TARGET:
        logger.info(
            f'[Refill] Pool suficiente: {current_pool}/{POOL_TARGET} leads no_enviado. '
            'Sin scraping necesario.'
        )
        return 0

    deficit = POOL_TARGET - current_pool
    logger.info(
        f'[Refill] Pool actual: {current_pool}/{POOL_TARGET}. '
        f'Buscando {deficit} leads nuevos para completar el pool...'
    )

    # ── Whitelist explícita: SOLO rubros de et_rubro_templates ──────────────
    allowed_rubros = _get_active_rubros()
    allowed_set    = {r.lower().strip() for r in allowed_rubros}

    with job_run('auto_scraping') as run:
        total_saved = 0
        # Pasar el déficit real como objetivo al generador de targets
        targets_raw = _get_intel_targets(deficit)

        targets = [
            (r, c, n) for r, c, n in targets_raw
            if r.lower().strip() in allowed_set
        ]
        skipped = len(targets_raw) - len(targets)
        if skipped:
            logger.warning(
                f'[Refill] {skipped} par(es) descartados por rubro fuera de whitelist.'
            )
        logger.info(
            f'[Refill] {len(targets)} pares rubro+comuna en cola '
            f'(objetivo: {deficit} leads)'
        )

        for rubro, comuna, max_items in targets:
            if total_saved >= deficit:
                logger.info(
                    f'[Refill] Déficit cubierto: {total_saved} leads nuevos. '
                    f'Pool estimado: {current_pool + total_saved}/{POOL_TARGET}'
                )
                break
            try:
                saved = _get_leads(rubro, comuna, max_items, send_emails=False)
                total_saved += saved
                logger.info(
                    f'[Refill] {rubro}/{comuna}: +{saved} leads '
                    f'(acum: {total_saved}/{deficit})'
                )
            except Exception as e:
                logger.error(f'[Refill] Error en {rubro}/{comuna}: {e}')

        run['count'] = total_saved
        pool_final = current_pool + total_saved
        logger.info(
            f'[Refill] Completado. Pool: {pool_final}/{POOL_TARGET} '
            f'({total_saved} leads nuevos agregados).'
        )

        # Backfill: asignar al Owner los contactos recién scrapeados que
        # quedaron con assigned_to=NULL. Mantiene el flujo histórico de
        # "el pool de email es del Owner por default".
        try:
            conn_bf = get_db()
            owner = conn_bf.execute(
                "SELECT id FROM users WHERE role='owner' AND status='active' "
                "ORDER BY id ASC LIMIT 1"
            ).fetchone()
            if owner:
                conn_bf.execute(
                    "UPDATE et_contacts SET assigned_to = ? WHERE assigned_to IS NULL",
                    (owner['id'],)
                )
                conn_bf.commit()
            conn_bf.close()
        except Exception as e:
            logger.warning(f'[Refill] Backfill assigned_to falló: {e}')
    return total_saved


def _run_email_batch_for_user(batch_size: int, lote_name: str,
                               user: dict | None, MAX_PER_RUBRO: int,
                               THROTTLE_SECS: int, COOLDOWN_DAYS: int) -> int:
    """
    Procesa un lote para un usuario específico (Sales) o para el pool global
    (cuando user is None — modo legacy Owner). Extraído de run_email_batch.
    """
    import time as _time
    from collections import defaultdict

    user_id = user['id'] if user else None
    user_label = f" · {user.get('full_name') or user.get('email')}" if user else ""

    # Si es per-user, validamos creds antes de gastar queries.
    # Owner usa env vars legacy → se permite continuar sin smtp_user en su perfil.
    user_role = (user or {}).get('role') or ''
    if user_id is not None and user_role != 'owner':
        creds = _resolve_user_creds(user_id)
        if not creds:
            logger.warning(f"[{lote_name}{user_label}] Sin SMTP — skip")
            return 0

    # ── Candidatos
    conn = get_db()
    if user_id is not None:
        candidatos = conn.execute(
            """SELECT id, business_name, email, rubro, comuna, campaign_status
               FROM et_contacts
               WHERE campaign_status IN ('no_enviado','pendiente')
                 AND assigned_to = ?
               ORDER BY
                   CASE campaign_status WHEN 'pendiente' THEN 0 ELSE 1 END,
                   created_at ASC
               LIMIT 800""",
            (user_id,)
        ).fetchall()
    else:
        candidatos = conn.execute(
            """SELECT id, business_name, email, rubro, comuna, campaign_status
               FROM et_contacts
               WHERE campaign_status IN ('no_enviado','pendiente')
               ORDER BY
                   CASE campaign_status WHEN 'pendiente' THEN 0 ELSE 1 END,
                   created_at ASC
               LIMIT 800"""
        ).fetchall()
    conn.close()

    rubro_counts: dict = defaultdict(int)
    selected = []
    for lead in candidatos:
        rk = (lead['rubro'] or '').lower().strip()
        if rubro_counts[rk] < MAX_PER_RUBRO:
            selected.append(lead)
            rubro_counts[rk] += 1
        if len(selected) >= batch_size:
            break

    logger.info(
        f'[{lote_name}{user_label}] {len(selected)} leads seleccionados '
        f'({len(candidatos)} candidatos, máx {MAX_PER_RUBRO}/rubro)'
    )

    total_sent = 0
    skipped_cd = 0

    for row in selected:
        email = (row['email'] or '').strip()
        if not email:
            continue

        # ── Cooldown 30 días por dominio
        domain = email.rsplit('@', 1)[-1].lower() if '@' in email else ''
        if domain:
            conn_cd = get_db()
            recently_sent = conn_cd.execute(
                """SELECT COUNT(*) FROM et_contacts
                   WHERE LOWER(email) LIKE ?
                     AND campaign_status NOT IN ('no_enviado','pendiente','opt_out')
                     AND fecha_envio >= datetime('now', ?)""",
                (f'%@{domain}', f'-{COOLDOWN_DAYS} days')
            ).fetchone()[0]
            conn_cd.close()
            if recently_sent > 0:
                skipped_cd += 1
                continue

        try:
            tpl     = _get_template_for_rubro(row['rubro'])
            subject = tpl['subject']
            body    = tpl['body'].replace('{nombre}', row['business_name'] or '')
            ok      = _send_email(
                          email, subject, body,
                          rubro=row['rubro'], contact_name=row['business_name'],
                          for_user_id=user_id,
                      )
            now         = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            followup_dt = (datetime.now() + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')

            conn2 = get_db()
            if ok:
                conn2.execute(
                    """UPDATE et_contacts
                       SET campaign_status='enviado', fecha_envio=?, proximo_seguimiento=?
                       WHERE id=?""",
                    (now, followup_dt, row['id'])
                )
                total_sent += 1
                logger.info(f'[{lote_name}{user_label}] ✉ {email} ({row["rubro"]})')
            else:
                conn2.execute(
                    "UPDATE et_contacts SET campaign_status='no_enviado' WHERE id=?",
                    (row['id'],)
                )
            conn2.commit()
            conn2.close()

            _time.sleep(THROTTLE_SECS)

        except Exception as e:
            logger.error(f'[{lote_name}{user_label}] Error enviando {email}: {e}')

    logger.info(
        f'[{lote_name}{user_label}] Completado: {total_sent} enviados, '
        f'{skipped_cd} saltados por cooldown.'
    )
    return total_sent


def run_email_batch(batch_size: int = 40, lote_name: str = 'Lote',
                    slot_field: str | None = None) -> int:
    """
    Envía un lote de emails desde el pool no_enviado.

    Reglas de envío implementadas:
    ─────────────────────────────────────────────────────────────────────────
    Regla 1 — Solo L-V: no envía sábado ni domingo.
    Regla 2 — Máx 8 emails por rubro por lote: diversifica el pipeline.
    Regla 4 — Cooldown 30 días por dominio (@empresa.cl): evita re-contactar.
    Regla 6 — Throttle 2s entre emails: evita flags de spam en Gmail.
    ─────────────────────────────────────────────────────────────────────────

    Lotes del día (configurados en app.py / scheduler_worker.py):
      09:00 L-V → run_email_batch(40, 'Lote Mañana')
      12:00 L-V → run_email_batch(35, 'Lote Mediodía')
      16:00 L-V → run_email_batch(25, 'Lote Tarde')
      Total: 100 emails/día L-V.

    Después de cada lote verifica el pool:
      pool < 100  → dispara refill inmediato en background.
      pool < 1000 → log informativo; el job 08:00 completa mañana.
    """
    from database import job_run
    from jobs.send_prospecting import get_users_active_for_slot

    MAX_PER_RUBRO    = 8
    THROTTLE_SECS    = 2
    COOLDOWN_DAYS    = 30
    REFILL_THRESHOLD = 100
    POOL_TARGET      = 1000

    if datetime.now().weekday() >= 5:
        logger.info(f'[{lote_name}] Fin de semana — sin envíos (Regla 1: L-V).')
        return 0

    logger.info(f'[{lote_name}] Iniciando — default batch {batch_size}, slot={slot_field}')

    with job_run(f'email_{lote_name.lower().replace(" ", "_")}') as run:
        total_sent = 0
        users = get_users_active_for_slot(slot_field) if slot_field else []
        if users:
            for u in users:
                per_user_limit = min(batch_size, int(u.get('daily_limit') or batch_size))
                total_sent += _run_email_batch_for_user(
                    per_user_limit, lote_name, u,
                    MAX_PER_RUBRO, THROTTLE_SECS, COOLDOWN_DAYS
                )
        else:
            logger.info(f'[{lote_name}] Sin usuarios con toggle activo — running pool global (Owner legacy)')
            total_sent = _run_email_batch_for_user(
                batch_size, lote_name, None,
                MAX_PER_RUBRO, THROTTLE_SECS, COOLDOWN_DAYS
            )

        run['count'] = total_sent

        # ── Verificar pool y disparar refill si es necesario ─────────────────
        conn3 = get_db()
        pool_restante = conn3.execute(
            "SELECT COUNT(*) FROM et_contacts WHERE campaign_status IN ('no_enviado','pendiente')"
        ).fetchone()[0]
        conn3.close()

        logger.info(f'[{lote_name}] Pool restante: {pool_restante}/{POOL_TARGET}')

        if pool_restante < REFILL_THRESHOLD:
            logger.warning(
                f'[{lote_name}] ⚠️ Pool bajo ({pool_restante} < {REFILL_THRESHOLD}). '
                'Iniciando refill en background...'
            )
            threading.Thread(target=run_intel_scraping, daemon=True, name='refill_leads').start()

    return total_sent


# Alias de backward-compat para código legado que llame a run_daily_prospecting
def run_daily_prospecting() -> int:
    """Alias legacy — envía los 100 en un solo bloque (sin lotes). Usar run_email_batch."""
    return run_email_batch(100, 'email_daily')


# ── Rubro → nombre de archivo de plantilla ────────────────────────────────────
RUBRO_TEMPLATE_KEY = {
    'cafetería':        'cafeteria',
    'pastelería':       'pasteleria',
    'sushi':            'sushi',
    'emporio':          'emporio',
    'clínica dental':   'clinica_dental',
    'clinicas dentales':'clinica_dental',
    'clinica dental':   'clinica_dental',
    'pizzería':         'pizzeria',
    'librería':         'libreria',
    'veterinaria':      'veterinaria',
    'florería':         'floreria',
    'oftalmología':     'oftalmologia',
    'tienda de muebles':'tienda_muebles',
    'lubricentro':      'lubricentro',
    'frenos':           'frenos',
    'spa':              'spa',
    # extras presentes en los templates (por si se incorporan al sistema)
    'clínica de belleza': 'clinica_belleza',
    'clinica belleza':    'clinica_belleza',
    'gimnasio':           'gimnasio',
    'pollos asados':      'pollos_asados',
    'ferretería':         'ferreteria',
    'ferreteria':         'ferreteria',
}

# Emojis por rubro para asunto del email
RUBRO_EMOJI = {
    'cafeteria':      '☕',
    'pasteleria':     '🎂',
    'sushi':          '🍣',
    'emporio':        '🧀',
    'clinica_dental': '🦷',
    'pizzeria':       '🍕',
    'libreria':       '📚',
    'veterinaria':    '🐾',
    'floreria':       '🌸',
    'oftalmologia':   '👁️',
    'tienda_muebles': '🛋️',
    'lubricentro':    '🛢️',
    'frenos':         '🔧',
    'spa':            '🌿',
    'clinica_belleza':'💎',
    'gimnasio':       '💪',
    'pollos_asados':  '🍗',
    'ferreteria':     '🔩',
}


def _load_followup_template(rubro: str, hours: int, nombre: str) -> str | None:
    """
    Carga la plantilla HTML de seguimiento para el rubro y las horas indicadas.
    Reemplaza [Nombre] con el nombre del negocio.
    Retorna el HTML listo para enviar, o None si no existe template.
    """
    import pathlib
    key = RUBRO_TEMPLATE_KEY.get(rubro.lower().strip())
    if not key:
        # fuzzy match: buscar la primera clave que esté contenida en rubro
        rubro_lower = rubro.lower().strip()
        for k, v in RUBRO_TEMPLATE_KEY.items():
            if k in rubro_lower or rubro_lower in k:
                key = v
                break
    if not key:
        return None

    tpl_path = (pathlib.Path(__file__).parent.parent
                / 'templates' / 'emails' / 'seguimiento'
                / f'seguimiento_{hours}h_{key}.html')
    if not tpl_path.exists():
        logger.debug(f'[EmailAuto] Template no encontrada: {tpl_path}')
        return None

    with open(tpl_path, 'r', encoding='utf-8') as f:
        html = f.read()

    nombre_safe = nombre or 'estimado'
    html = html.replace('[Nombre]', nombre_safe)
    return html


def _build_followup_subject(rubro: str, hours: int, nombre: str) -> str:
    """Genera el asunto del email de seguimiento."""
    key = RUBRO_TEMPLATE_KEY.get(rubro.lower().strip(), '')
    emoji = RUBRO_EMOJI.get(key, '📩')
    nombre_safe = nombre or 'estimado'
    if hours == 48:
        return f'{emoji} ¿Todo bien, {nombre_safe}? Te escribo de nuevo — Mercado Pago'
    else:
        return f'{emoji} Último mensaje, {nombre_safe} — ¿lo dejamos aquí? — Mercado Pago'


def run_followup():
    """
    Job de seguimiento automático:
    - count=0 (primer seguimiento): envía plantilla 48h, programa próximo en +48h
    - count=1 (segundo seguimiento): envía plantilla 96h, marca 'no_responde', detiene ciclo
    - count>=2: omite el contacto (ya completó el ciclo de seguimientos)
    En ambos casos registra en et_seguimientos con tipo='email_48h' o 'email_96h'.
    Solo actúa sobre contactos que NO respondieron (estado_interes NOT IN interesado/respondido/cerrado/etc.)
    """
    from database import job_run
    import os
    from routes.email_tool import _send_smtp_followup

    logger.info('[EmailAuto] Iniciando job de seguimiento (48h/96h)...')
    conn = get_db()
    now = datetime.now()
    threshold = now.strftime('%Y-%m-%d %H:%M:%S')

    # Si hay usuarios con email_followup_active, filtramos por sus contactos.
    # Si no hay ninguno → modo legacy global (Owner).
    from jobs.send_prospecting import get_users_active_for_slot
    fu_users = get_users_active_for_slot('email_followup_active')
    fu_user_ids = [u['id'] for u in fu_users]

    if fu_user_ids:
        placeholders = ','.join('?' for _ in fu_user_ids)
        contacts = conn.execute(
            f"""SELECT *
               FROM et_contacts
               WHERE estado_interes NOT IN ('respondido','interesado','quiere_reunion','cerrado','opt_out')
                 AND campaign_status NOT IN ('no_responde','opt_out')
                 AND proximo_seguimiento IS NOT NULL
                 AND proximo_seguimiento <= ?
                 AND seguimiento_count < 2
                 AND assigned_to IN ({placeholders})
               ORDER BY proximo_seguimiento ASC
               LIMIT 50""",
            (threshold, *fu_user_ids)
        ).fetchall()
    else:
        contacts = conn.execute(
            """SELECT *
               FROM et_contacts
               WHERE estado_interes NOT IN ('respondido','interesado','quiere_reunion','cerrado','opt_out')
                 AND campaign_status NOT IN ('no_responde','opt_out')
                 AND proximo_seguimiento IS NOT NULL
                 AND proximo_seguimiento <= ?
                 AND seguimiento_count < 2
               ORDER BY proximo_seguimiento ASC
               LIMIT 50""",
            (threshold,)
        ).fetchall()

    sent = 0
    errors = 0
    now_str = now.strftime('%Y-%m-%d %H:%M:%S')
    booking_url = os.getenv('BOOKING_URL', 'https://calendly.com/juansebastian-pinto/mercadopago')

    for c in contacts:
        count   = c['seguimiento_count'] or 0
        hours   = 48 if count == 0 else 96
        tipo    = f'email_{hours}h'
        rubro   = c['rubro'] or 'negocio'
        nombre  = c['business_name'] or 'estimado'
        email   = c['email']

        subject = _build_followup_subject(rubro, hours, nombre)

        # Enviar con el mismo pipeline que los emails de prospección:
        # header GIF animado + POS GIF en firma + foto de firma (todos via CID)
        # Per-Sales: resolver creds del dueño del contacto.
        # Owner → env legacy; Sales/TL → sus creds; sin creds → skip.
        owner_uid = c['assigned_to'] if 'assigned_to' in c.keys() else None
        user_creds = None
        if owner_uid:
            urow = conn.execute(
                "SELECT role FROM users WHERE id = ?", (owner_uid,)
            ).fetchone()
            if urow and urow['role'] == 'owner':
                user_creds = None  # env vars legacy
            else:
                user_creds = _resolve_user_creds(owner_uid)
                if not user_creds:
                    logger.warning(f'[EmailAuto] followup skip — user {owner_uid} sin SMTP')
                    continue
        result = _send_smtp_followup(
            to_email=email,
            subject=subject,
            rubro=rubro,
            contact_name=nombre,
            hours=hours,
            booking_url=booking_url,
            user_creds=user_creds,
        )

        ok = result.get('ok', False)
        new_count = count + 1

        if hours == 48:
            # Siguiente seguimiento en 48 horas más (= 96h desde email original)
            next_followup = (now + timedelta(hours=48)).strftime('%Y-%m-%d %H:%M:%S')
            new_status = 'seguimiento_48h'
        else:
            # Ciclo completado: no más seguimientos automáticos
            next_followup = None
            new_status = 'no_responde'

        conn.execute(
            '''UPDATE et_contacts
               SET seguimiento_count     = ?,
                   last_followup_at      = ?,
                   proximo_seguimiento   = ?,
                   campaign_status       = ?
               WHERE id = ?''',
            (new_count, now_str, next_followup, new_status, c['id'])
        )
        conn.execute(
            '''INSERT INTO et_seguimientos (contact_id, tipo, fecha, notas, resultado)
               VALUES (?, ?, ?, ?, 'sin_respuesta')''',
            (c['id'], tipo, now_str,
             f'Seguimiento automático {hours}h — {"enviado" if ok else "error: " + result.get("error","?")}')
        )

        if ok:
            sent += 1
            logger.info(f'[EmailAuto] Seguimiento {hours}h enviado a {email} ({rubro}) — count={new_count}')
        else:
            errors += 1
            logger.error(f'[EmailAuto] Error seguimiento {hours}h a {email}: {result.get("error")}')

    conn.commit()
    conn.close()
    logger.info(f'[EmailAuto] Seguimientos completados: {sent} enviados, {errors} errores de {len(contacts)} pendientes')
    _log_followup_run(sent)
    return {'sent': sent, 'errors': errors, 'total': len(contacts)}


def _log_followup_run(sent: int):
    """Registra el resultado del seguimiento en job_runs."""
    from database import get_db
    from datetime import datetime
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    conn = get_db()
    conn.execute(
        'INSERT INTO job_runs (job_id, started_at, finished_at, status, result_count) VALUES (?,?,?,?,?)',
        ('email_followup', now, now, 'done', sent)
    )
    conn.commit()
    conn.close()


# ── Thread wrappers para los 3 lotes diarios ─────────────────────────────────

def run_lote_manana():
    return run_email_batch(40, 'Lote Mañana', slot_field='email_lote1_active')

def run_lote_mediodia():
    return run_email_batch(35, 'Lote Mediodía', slot_field='email_lote2_active')

def run_lote_tarde():
    return run_email_batch(25, 'Lote Tarde', slot_field='email_lote3_active')


def run_lote_manana_in_thread():
    """09:00 L-V — 40 emails (Lote Mañana). Pasa slot_field para gating per-user."""
    threading.Thread(
        target=run_email_batch,
        kwargs={'batch_size':40, 'lote_name':'Lote Mañana', 'slot_field':'email_lote1_active'},
        daemon=True
    ).start()

def run_lote_mediodia_in_thread():
    """12:00 L-V — 35 emails (Lote Mediodía)."""
    threading.Thread(
        target=run_email_batch,
        kwargs={'batch_size':35, 'lote_name':'Lote Mediodía', 'slot_field':'email_lote2_active'},
        daemon=True
    ).start()

def run_lote_tarde_in_thread():
    """16:00 L-V — 25 emails (Lote Tarde)."""
    threading.Thread(
        target=run_email_batch,
        kwargs={'batch_size':25, 'lote_name':'Lote Tarde', 'slot_field':'email_lote3_active'},
        daemon=True
    ).start()

# Legacy (usado por disparos manuales del dashboard)
def run_daily_in_thread():
    threading.Thread(target=run_email_batch, args=(100, 'email_daily'), daemon=True).start()

def run_intel_scraping_in_thread():
    threading.Thread(target=run_intel_scraping, daemon=True).start()

def run_followup_in_thread():
    threading.Thread(target=run_followup, daemon=True).start()
