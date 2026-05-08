"""
Validador rápido de emails: formato + MX DNS + filtros de calidad.

Uso:
    from email_validator_mx import is_valid_business_email
    if is_valid_business_email('contacto@empresa.cl'):
        ...

- format_ok: regex RFC-básico.
- domain_has_mx: consulta DNS MX (cache 24h, timeout 3s).
- not_disposable: rechaza dominios temporales (mailinator, 10minutemail, etc.).
- not_role_blacklist: opt-out de emails que rebotan mucho (noreply@, etc.).

Pensado para correr durante el scraping (jobs/email_automation.py) antes de
INSERT en et_contacts. Filtra ~80-90% de los rebotes futuros.
"""
import re
import time
import logging
from typing import Tuple

logger = logging.getLogger(__name__)

# Cache de dominios validados: { 'dominio.cl': (timestamp, has_mx) }
_MX_CACHE: dict = {}
_MX_CACHE_TTL = 24 * 3600  # 24h

# Regex razonable para emails (no es 100% RFC pero filtra basura)
_EMAIL_RE = re.compile(
    r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$'
)

# Dominios desechables conocidos
_DISPOSABLE_DOMAINS = {
    'mailinator.com', '10minutemail.com', 'guerrillamail.com', 'tempmail.com',
    'throwaway.email', 'temp-mail.org', 'yopmail.com', 'sharklasers.com',
    'getnada.com', 'maildrop.cc', 'fake-mail.com', 'trashmail.com',
    'discard.email', 'mintemail.com', 'temporary-mail.net',
}

# Localparts que tienden a rebotar o son distribuidores genéricos sin dueño
# Configurable: si querés mantener "info@" porque te funciona, comentá la línea.
_NOREPLY_LOCAL_PARTS = {
    'noreply', 'no-reply', 'donotreply', 'do-not-reply', 'mailer-daemon',
    'postmaster', 'abuse', 'spam',
}

# Dominios públicos que rara vez son negocios (preferir email corporativo)
# El scraper igual los puede aceptar — NO los bloqueamos por default.
_PERSONAL_DOMAINS = {
    'gmail.com', 'googlemail.com', 'hotmail.com', 'hotmail.cl', 'outlook.com',
    'outlook.cl', 'yahoo.com', 'yahoo.cl', 'live.com', 'live.cl', 'icloud.com',
}


def _format_ok(email: str) -> bool:
    return bool(email and _EMAIL_RE.match(email.strip()))


def _is_disposable(email: str) -> bool:
    domain = email.rsplit('@', 1)[-1].lower()
    return domain in _DISPOSABLE_DOMAINS


def _is_noreply(email: str) -> bool:
    local = email.split('@', 1)[0].lower()
    return local in _NOREPLY_LOCAL_PARTS


def _has_mx_record(domain: str, timeout: float = 3.0) -> bool:
    """
    Consulta MX record con cache en memoria.
    Si dnspython no está instalado, devuelve True (fail-open para no bloquear scraping).
    """
    domain = (domain or '').lower().strip()
    if not domain:
        return False
    now = time.time()
    cached = _MX_CACHE.get(domain)
    if cached and (now - cached[0]) < _MX_CACHE_TTL:
        return cached[1]
    try:
        import dns.resolver  # type: ignore
        resolver = dns.resolver.Resolver()
        resolver.timeout = timeout
        resolver.lifetime = timeout
        answers = resolver.resolve(domain, 'MX')
        ok = len(answers) > 0
    except ImportError:
        logger.warning("[EmailValidator] dnspython no instalado, skip MX check")
        ok = True  # fail-open
    except Exception as e:
        logger.debug(f"[EmailValidator] MX fail {domain}: {e}")
        ok = False
    _MX_CACHE[domain] = (now, ok)
    return ok


def is_valid_business_email(
    email: str,
    *,
    require_mx: bool = True,
    block_disposable: bool = True,
    block_noreply: bool = True,
    block_personal_domains: bool = False,
) -> Tuple[bool, str]:
    """
    Valida un email. Retorna (ok, motivo) — motivo='' si ok=True.

    Args:
        require_mx: requiere MX record en DNS (recomendado).
        block_disposable: rechaza dominios temporales.
        block_noreply: rechaza locals tipo noreply@, postmaster@.
        block_personal_domains: rechaza @gmail/@hotmail (no recomendado, los locales
            chilenos usan mucho @gmail).
    """
    if not _format_ok(email):
        return False, 'formato_invalido'
    e = email.strip().lower()
    if block_disposable and _is_disposable(e):
        return False, 'dominio_desechable'
    if block_noreply and _is_noreply(e):
        return False, 'noreply'
    domain = e.rsplit('@', 1)[-1]
    if block_personal_domains and domain in _PERSONAL_DOMAINS:
        return False, 'dominio_personal'
    if require_mx and not _has_mx_record(domain):
        return False, 'sin_mx_record'
    return True, ''


def validate_quick(email: str) -> bool:
    """Helper: True si el email es válido para prospección."""
    ok, _ = is_valid_business_email(email)
    return ok
