"""
Scrapers de directorios chilenos para complementar Brave/Outscraper/CSE.

Fuentes:
- PáginasAmarillas.cl  → directorio formal nacional
- Guíalocal.cl         → negocios locales por comuna

Cada función:
- Toma (rubro, comuna, max_results, send_emails=False)
- Inserta en et_contacts con source_query='paginas_amarillas:rubro+comuna' o 'guialocal:rubro+comuna'
- Reusa _is_valid_business_email() y _has_mx_record() del filtro existente
- Retorna cantidad insertada

Diseño defensivo: si la fuente cambia su HTML / responde 403 / timeout, el
scraper devuelve 0 y loguea, sin tirar excepción al pipeline.
"""
import re
import time
import logging
import requests
from urllib.parse import quote_plus
from datetime import datetime

logger = logging.getLogger(__name__)

# Header user-agent realista para evitar bloqueos triviales
_HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) '
                  'AppleWebKit/537.36 (KHTML, like Gecko) '
                  'Chrome/124.0 Safari/537.36',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'es-CL,es;q=0.9',
}

# Pausa entre requests para no saturar
_REQUEST_DELAY = 1.5  # segundos

# Regex de email
_EMAIL_RE = re.compile(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+')


def _http_get(url: str, timeout: int = 15) -> str | None:
    """GET con manejo de errores. Retorna texto o None."""
    try:
        r = requests.get(url, headers=_HEADERS, timeout=timeout)
        if r.status_code != 200:
            logger.debug(f"[ScraperCL] {url} status={r.status_code}")
            return None
        return r.text
    except Exception as e:
        logger.debug(f"[ScraperCL] {url} error: {e}")
        return None


def _extract_emails_from_html(html: str) -> list[str]:
    """Extrae todos los emails únicos del HTML."""
    if not html:
        return []
    found = _EMAIL_RE.findall(html)
    # Normalizar y deduplicar
    seen = set()
    out = []
    for e in found:
        e = e.lower().strip()
        if e in seen:
            continue
        seen.add(e)
        out.append(e)
    return out


def _save_contact(conn, business_name: str, email: str,
                   rubro: str, comuna: str, source_query: str,
                   ciudad: str = 'Santiago', address: str = '') -> bool:
    """
    Inserta un et_contact si no existe. Retorna True si insertó nuevo.
    Reusa el filtro de calidad existente.
    """
    from jobs.email_automation import _is_valid_business_email
    if not _is_valid_business_email(email):
        return False
    # Dedup por email
    existing = conn.execute(
        "SELECT id FROM et_contacts WHERE LOWER(TRIM(email)) = LOWER(TRIM(?))",
        (email,)
    ).fetchone()
    if existing:
        return False
    conn.execute(
        '''INSERT INTO et_contacts
           (business_name, email, rubro, ciudad, comuna, address,
            campaign_status, source_query, created_at)
           VALUES (?, ?, ?, ?, ?, ?, 'no_enviado', ?, datetime('now','localtime'))''',
        (business_name, email, rubro, ciudad, comuna, address, source_query)
    )
    return True


# ════════════════════════════════════════════════════════════════════
# PáginasAmarillas.cl
# ════════════════════════════════════════════════════════════════════
def scrape_paginas_amarillas(rubro: str, comuna: str,
                              max_results: int = 20,
                              send_emails: bool = False) -> int:
    """
    Scrapea PáginasAmarillas.cl para un rubro+comuna.
    URL típica: https://www.paginasamarillas.cl/buscar/<rubro>/<comuna>

    Retorna cantidad de leads NUEVOS guardados.
    """
    from database import get_db
    rubro_q  = quote_plus(rubro.lower().strip())
    comuna_q = quote_plus(comuna.lower().strip())
    base_url = f'https://www.paginasamarillas.cl/buscar/{rubro_q}/{comuna_q}'

    logger.info(f"[PA.cl] Buscando {rubro} en {comuna}")
    listing_html = _http_get(base_url)
    if not listing_html:
        logger.info(f"[PA.cl] Sin resultados para {rubro}/{comuna}")
        return 0

    # Extraer URLs de fichas de negocio (heurística: links a /negocio/ o /empresa/)
    detail_urls = re.findall(
        r'href="(https?://[^"]*paginasamarillas\.cl/[^"]*?(?:negocio|empresa|ficha)[^"]*)"',
        listing_html
    )
    # Deduplicar
    detail_urls = list(dict.fromkeys(detail_urls))[:max_results * 3]

    # Plan B: si no hay fichas, sacamos emails directos del listing
    if not detail_urls:
        emails = _extract_emails_from_html(listing_html)
        return _bulk_save_emails(emails, listing_html, rubro, comuna,
                                  source='paginas_amarillas', max_results=max_results)

    saved = 0
    conn = get_db()
    for url in detail_urls:
        if saved >= max_results:
            break
        time.sleep(_REQUEST_DELAY)
        ficha = _http_get(url)
        if not ficha:
            continue
        emails = _extract_emails_from_html(ficha)
        if not emails:
            continue
        # Heurística: primer h1 / title del HTML como business_name
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', ficha) or re.search(r'<title>([^<]+)</title>', ficha)
        business_name = (m.group(1).strip()[:120] if m else f'{rubro.title()} {comuna}')
        for em in emails[:3]:  # máx 3 emails por ficha
            if _save_contact(conn, business_name, em, rubro, comuna,
                              source_query=f'paginas_amarillas:{rubro}+{comuna}',
                              ciudad='Santiago'):
                saved += 1
                if saved >= max_results:
                    break
    conn.commit()
    conn.close()
    logger.info(f"[PA.cl] {rubro}/{comuna}: {saved} nuevos")
    return saved


# ════════════════════════════════════════════════════════════════════
# Guíalocal.cl
# ════════════════════════════════════════════════════════════════════
def scrape_guialocal(rubro: str, comuna: str,
                      max_results: int = 20,
                      send_emails: bool = False) -> int:
    """
    Scrapea Guíalocal.cl para un rubro+comuna.
    URL típica: https://www.guialocal.cl/<comuna>/<rubro>
    """
    from database import get_db
    rubro_q  = rubro.lower().strip().replace(' ', '-')
    comuna_q = comuna.lower().strip().replace(' ', '-')
    base_url = f'https://www.guialocal.cl/{comuna_q}/{rubro_q}'

    logger.info(f"[Guíalocal] Buscando {rubro} en {comuna}")
    listing_html = _http_get(base_url)
    if not listing_html:
        return 0

    detail_urls = re.findall(
        r'href="(https?://[^"]*guialocal\.cl/[^"]*?(?:empresa|negocio|comercio)[^"]*)"',
        listing_html
    )
    detail_urls = list(dict.fromkeys(detail_urls))[:max_results * 3]

    if not detail_urls:
        emails = _extract_emails_from_html(listing_html)
        return _bulk_save_emails(emails, listing_html, rubro, comuna,
                                  source='guialocal', max_results=max_results)

    saved = 0
    conn = get_db()
    for url in detail_urls:
        if saved >= max_results:
            break
        time.sleep(_REQUEST_DELAY)
        ficha = _http_get(url)
        if not ficha:
            continue
        emails = _extract_emails_from_html(ficha)
        if not emails:
            continue
        m = re.search(r'<h1[^>]*>([^<]+)</h1>', ficha) or re.search(r'<title>([^<]+)</title>', ficha)
        business_name = (m.group(1).strip()[:120] if m else f'{rubro.title()} {comuna}')
        for em in emails[:3]:
            if _save_contact(conn, business_name, em, rubro, comuna,
                              source_query=f'guialocal:{rubro}+{comuna}',
                              ciudad='Santiago'):
                saved += 1
                if saved >= max_results:
                    break
    conn.commit()
    conn.close()
    logger.info(f"[Guíalocal] {rubro}/{comuna}: {saved} nuevos")
    return saved


# ════════════════════════════════════════════════════════════════════
# Helper: guardado masivo cuando no hay fichas individuales
# ════════════════════════════════════════════════════════════════════
def _bulk_save_emails(emails: list[str], html: str,
                       rubro: str, comuna: str,
                       source: str, max_results: int) -> int:
    """Guarda emails sueltos extraídos del listing si no se pudieron parsear fichas."""
    from database import get_db
    if not emails:
        return 0
    saved = 0
    conn = get_db()
    for em in emails[:max_results]:
        # business_name genérico (no tenemos contexto)
        business_name = f'{rubro.title()} {comuna}'
        if _save_contact(conn, business_name, em, rubro, comuna,
                          source_query=f'{source}:{rubro}+{comuna}',
                          ciudad='Santiago'):
            saved += 1
    conn.commit()
    conn.close()
    return saved
