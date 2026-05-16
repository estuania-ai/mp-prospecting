"""
Twilio WhatsApp Client — backend alternativo a Evolution.

Reemplaza evolution_client cuando el número está aprobado en Twilio.
Cumple la interfaz BotClient (send_text, send_image) usada por el dispatcher.

Configuración requerida (env vars):
  TWILIO_ACCOUNT_SID       Account SID de tu cuenta Twilio (empieza con AC...)
  TWILIO_AUTH_TOKEN        Token secreto · NUNCA commitear · NUNCA loguear
  TWILIO_WHATSAPP_FROM     Número de envío con prefijo 'whatsapp:+56935103447'
  TWILIO_MESSAGING_SID     (opcional) Messaging Service SID si se usa servicio

Selección de backend desde el dispatcher:
  WA_BACKEND=twilio        Activa este cliente
  WA_BACKEND=evolution     (default) Mantiene Evolution
"""
from __future__ import annotations
import os
import hmac
import hashlib
import base64
import logging
from typing import Optional
from urllib.parse import urlparse

import requests

logger = logging.getLogger(__name__)


# ── CONFIG ──────────────────────────────────────────────────────
def _account_sid() -> str:
    return os.getenv("TWILIO_ACCOUNT_SID", "")


def _auth_token() -> str:
    """
    Devuelve el Auth Token de Twilio.
    CRÍTICO: este valor NUNCA se loguea, NUNCA se persiste, NUNCA se expone
    en respuestas HTTP. Si se filtra, alguien puede mandar mensajes con
    identidad 'Sebastian Pinto - Mercado Pago' a clientes reales.
    """
    return os.getenv("TWILIO_AUTH_TOKEN", "")


def _from_number() -> str:
    """
    Número de origen formato Twilio: 'whatsapp:+56935103447'
    Si no tiene el prefijo 'whatsapp:', lo agregamos automáticamente.
    """
    n = os.getenv("TWILIO_WHATSAPP_FROM", "").strip()
    if n and not n.startswith("whatsapp:"):
        n = "whatsapp:" + n
    return n


def _messaging_sid() -> str:
    return os.getenv("TWILIO_MESSAGING_SID", "").strip()


def _api_base() -> str:
    sid = _account_sid()
    return f"https://api.twilio.com/2010-04-01/Accounts/{sid}"


def _timeout() -> int:
    return 20


# ── NORMALIZACIÓN DE TELÉFONO ───────────────────────────────────
def _normalize_to(phone: str) -> str:
    """
    Convierte un teléfono a formato Twilio WhatsApp 'whatsapp:+56XXXXXXXXX'.
    Acepta entradas: '56932320023', '+56932320023', '932320023',
    'whatsapp:+56932320023'.
    """
    if not phone:
        return ""
    p = phone.strip()
    if p.startswith("whatsapp:"):
        return p
    # solo dígitos
    digits = "".join(ch for ch in p if ch.isdigit())
    if not digits:
        return ""
    # asume CL si arranca con 9 (móvil chileno sin código país)
    if digits.startswith("9") and len(digits) == 9:
        digits = "56" + digits
    return f"whatsapp:+{digits}"


# ── ENVÍO DE MENSAJES ───────────────────────────────────────────
def send_text(phone: str, message: str,
              instance: Optional[str] = None) -> dict:
    """
    Envía mensaje de texto vía Twilio. Devuelve dict {ok, sid, error?}.

    El parámetro `instance` se ignora (Twilio no usa instancias como Evolution).
    Se mantiene en la firma para cumplir el Protocol BotClient.
    """
    sid = _account_sid()
    tok = _auth_token()
    frm = _from_number()
    if not (sid and tok and frm):
        logger.error("[Twilio] credenciales o número origen no configurados")
        return {"ok": False, "error": "twilio_misconfigured"}

    to = _normalize_to(phone)
    if not to:
        return {"ok": False, "error": "invalid_phone"}

    data = {
        "From": frm,
        "To":   to,
        "Body": message,
    }
    msg_sid = _messaging_sid()
    if msg_sid:
        # Si hay Messaging Service configurado, lo usamos (mejor para volumen)
        data["MessagingServiceSid"] = msg_sid

    try:
        r = requests.post(
            f"{_api_base()}/Messages.json",
            data=data,
            auth=(sid, tok),
            timeout=_timeout(),
        )
        if r.status_code >= 300:
            # Nunca logueamos el response completo porque puede incluir
            # PII del receptor en algunos casos. Solo el código y un excerpt.
            logger.warning(
                f"[Twilio] send_text fail status={r.status_code} "
                f"to_hash={_phone_hash(to)} excerpt={r.text[:120]}"
            )
            return {
                "ok": False,
                "status": r.status_code,
                "error": r.text[:200],
            }
        body = r.json()
        return {
            "ok":   True,
            "sid":  body.get("sid"),
            "data": body,
        }
    except Exception as e:
        logger.error(f"[Twilio] send_text exception: {e}")
        return {"ok": False, "error": str(e)[:200]}


def send_image(phone: str, image_url: str, caption: str = "",
               instance: Optional[str] = None) -> dict:
    """
    Envía imagen con caption opcional vía Twilio MediaUrl.
    image_url debe ser HTTPS público accesible por Twilio.
    """
    sid = _account_sid()
    tok = _auth_token()
    frm = _from_number()
    if not (sid and tok and frm):
        return {"ok": False, "error": "twilio_misconfigured"}

    to = _normalize_to(phone)
    if not to:
        return {"ok": False, "error": "invalid_phone"}

    # Twilio exige que MediaUrl sea HTTPS y accesible públicamente
    if not image_url.startswith("https://"):
        return {"ok": False, "error": "media_url_must_be_https"}

    data = {
        "From":     frm,
        "To":       to,
        "MediaUrl": image_url,
    }
    if caption:
        data["Body"] = caption
    msg_sid = _messaging_sid()
    if msg_sid:
        data["MessagingServiceSid"] = msg_sid

    try:
        r = requests.post(
            f"{_api_base()}/Messages.json",
            data=data,
            auth=(sid, tok),
            timeout=_timeout(),
        )
        if r.status_code >= 300:
            logger.warning(
                f"[Twilio] send_image fail status={r.status_code} "
                f"to_hash={_phone_hash(to)} excerpt={r.text[:120]}"
            )
            return {"ok": False, "status": r.status_code, "error": r.text[:200]}
        return {"ok": True, "data": r.json()}
    except Exception as e:
        logger.error(f"[Twilio] send_image exception: {e}")
        return {"ok": False, "error": str(e)[:200]}


# ── VALIDACIÓN DE WEBHOOK (HMAC) ────────────────────────────────
def validate_webhook_signature(url: str, params: dict,
                                 signature_header: str) -> bool:
    """
    Valida la firma X-Twilio-Signature de un webhook entrante.

    Sin esta validación, cualquier POST anónimo a /api/twilio/webhook
    puede inyectar mensajes falsos al dispatcher del bot (CWE-345:
    Insufficient Verification of Data Authenticity).

    Algoritmo Twilio:
      1. Tomar la URL completa del webhook
      2. Ordenar params POST alfabéticamente por key
      3. Concatenar URL + key1value1 + key2value2 + ...
      4. HMAC-SHA1 con auth_token como key
      5. Base64 del resultado
      6. Comparar con X-Twilio-Signature en tiempo constante

    Args:
        url: URL completa del webhook (incluye query string)
        params: dict con los params POST (request.form)
        signature_header: valor del header X-Twilio-Signature
    """
    tok = _auth_token()
    if not (tok and signature_header):
        return False

    # Build the string to sign: URL + sorted(key+value)
    data = url
    for key in sorted(params.keys()):
        data += key + (params[key] or "")

    mac = hmac.new(
        tok.encode("utf-8"),
        data.encode("utf-8"),
        hashlib.sha1,
    )
    expected = base64.b64encode(mac.digest()).decode("utf-8")

    # Comparación en tiempo constante para evitar timing attacks (CWE-208)
    return hmac.compare_digest(expected, signature_header)


# ── HELPERS INTERNOS ────────────────────────────────────────────
def _phone_hash(phone: str) -> str:
    """
    Devuelve un hash corto del teléfono para logs · evita persistir PII
    en logs sin necesidad (CWE-532: sensitive info in log file).
    """
    if not phone:
        return "EMPTY"
    return hashlib.sha256(phone.encode("utf-8")).hexdigest()[:10]


def is_configured() -> bool:
    """True si las 3 variables mínimas están seteadas."""
    return bool(_account_sid() and _auth_token() and _from_number())


def health_check() -> dict:
    """
    Verifica que las credenciales sean válidas pegando un GET no-destructivo
    al endpoint de cuenta. NO envía mensajes ni cambia nada.
    """
    sid = _account_sid()
    tok = _auth_token()
    if not (sid and tok):
        return {"ok": False, "error": "missing_credentials"}
    try:
        r = requests.get(
            f"{_api_base()}.json",
            auth=(sid, tok),
            timeout=10,
        )
        if r.status_code == 200:
            data = r.json()
            return {
                "ok":            True,
                "friendly_name": data.get("friendly_name"),
                "status":        data.get("status"),
                "type":          data.get("type"),
            }
        return {"ok": False, "status": r.status_code, "error": r.text[:200]}
    except Exception as e:
        return {"ok": False, "error": str(e)[:200]}
