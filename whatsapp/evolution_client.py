"""
Evolution API Client — reemplaza el sender Selenium.
Documentación: https://doc.evolution-api.com/

Configuración en .env:
  EVOLUTION_API_URL=http://localhost:8080   (o URL en Railway)
  EVOLUTION_API_KEY=tu_api_key
  EVOLUTION_INSTANCE=mp_prospecting
"""

import os
import logging
import requests
from datetime import datetime
from typing import Optional

logger = logging.getLogger(__name__)

# ── CONFIG ──────────────────────────────────────────────────────
def _base_url() -> str:
    return os.getenv('EVOLUTION_API_URL', 'http://localhost:8080').rstrip('/')

def _api_key() -> str:
    return os.getenv('EVOLUTION_API_KEY', '')

def _instance() -> str:
    return os.getenv('EVOLUTION_INSTANCE', 'mp_prospecting')

def _headers() -> dict:
    return {
        'apikey': _api_key(),
        'Content-Type': 'application/json',
    }

def _timeout() -> int:
    return 20


# ── INSTANCIA ────────────────────────────────────────────────────
def create_instance() -> dict:
    """Crea la instancia en Evolution API (solo una vez)."""
    try:
        r = requests.post(
            f"{_base_url()}/instance/create",
            headers=_headers(),
            json={
                "instanceName": _instance(),
                "token":        _api_key(),
                "qrcode":       True,
                "integration":  "WHATSAPP-BAILEYS",
            },
            timeout=_timeout(),
        )
        data = r.json()
        logger.info(f"[Evolution] Instancia creada: {data}")
        return {"ok": True, "data": data}
    except Exception as e:
        logger.error(f"[Evolution] Error creando instancia: {e}")
        return {"ok": False, "error": str(e)}


def get_connection_state() -> dict:
    """Retorna el estado de conexión: open / connecting / close."""
    try:
        r = requests.get(
            f"{_base_url()}/instance/connectionState/{_instance()}",
            headers=_headers(),
            timeout=_timeout(),
        )
        data = r.json()
        state = data.get("instance", {}).get("state", "unknown")
        return {"ok": True, "state": state, "raw": data}
    except Exception as e:
        logger.error(f"[Evolution] Error obteniendo estado: {e}")
        return {"ok": False, "state": "error", "error": str(e)}


def get_qr_code() -> dict:
    """Obtiene el QR code para escanear (base64 PNG)."""
    try:
        r = requests.get(
            f"{_base_url()}/instance/connect/{_instance()}",
            headers=_headers(),
            timeout=_timeout(),
        )
        data = r.json()
        qr_base64 = (
            data.get("base64")
            or data.get("qrcode", {}).get("base64")
            or data.get("code")
        )
        return {"ok": True, "qr": qr_base64, "raw": data}
    except Exception as e:
        logger.error(f"[Evolution] Error obteniendo QR: {e}")
        return {"ok": False, "error": str(e)}


def logout_instance() -> dict:
    """Desconecta la instancia (cierra sesión WhatsApp)."""
    try:
        r = requests.delete(
            f"{_base_url()}/instance/logout/{_instance()}",
            headers=_headers(),
            timeout=_timeout(),
        )
        return {"ok": r.status_code < 300}
    except Exception as e:
        logger.error(f"[Evolution] Error desconectando: {e}")
        return {"ok": False, "error": str(e)}


def restart_instance() -> dict:
    """Reinicia la instancia (útil si se cuelga)."""
    try:
        r = requests.put(
            f"{_base_url()}/instance/restart/{_instance()}",
            headers=_headers(),
            timeout=_timeout(),
        )
        return {"ok": r.status_code < 300}
    except Exception as e:
        logger.error(f"[Evolution] Error reiniciando: {e}")
        return {"ok": False, "error": str(e)}


# ── ENVÍO DE MENSAJES ────────────────────────────────────────────
def _normalize_phone(phone: str) -> str:
    """Asegura formato internacional sin +: 56912345678"""
    digits = ''.join(filter(str.isdigit, phone))
    if digits.startswith('0'):
        digits = digits[1:]
    if len(digits) == 9 and not digits.startswith('56'):
        digits = '56' + digits
    return digits


def is_mobile_phone(phone: str) -> bool:
    """Verifica que sea número móvil chileno (569XXXXXXXX).
    Filtra fijos (562, 563, etc.) que WhatsApp no acepta."""
    digits = _normalize_phone(phone)
    # Número móvil chileno: 569 + 8 dígitos = 11 dígitos totales
    return digits.startswith('569') and len(digits) == 11


def send_text(phone: str, message: str) -> dict:
    """Envía mensaje de texto plano. Solo números móviles (569XXXXXXXX)."""
    number = _normalize_phone(phone)
    if not is_mobile_phone(phone):
        logger.warning(f"[Evolution] Número no móvil ignorado: {number}")
        return {"ok": False, "phone": number, "error": "not_mobile", "skipped": True}
    try:
        r = requests.post(
            f"{_base_url()}/message/sendText/{_instance()}",
            headers=_headers(),
            json={
                "number":  number,
                "options": {"delay": 1500, "presence": "composing"},
                "textMessage": {"text": message},
            },
            timeout=_timeout(),
        )
        data = r.json()
        ok = r.status_code < 300 and data.get("key") is not None
        if ok:
            logger.info(f"[Evolution] Texto enviado → {number}")
        else:
            logger.warning(f"[Evolution] Fallo texto → {number}: {data}")
        return {"ok": ok, "phone": number, "data": data, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[Evolution] Error enviando texto a {number}: {e}")
        return {"ok": False, "phone": number, "error": str(e)}


def send_image(phone: str, image_url: str, caption: str = "") -> dict:
    """Envía imagen con caption opcional. Solo números móviles (569XXXXXXXX)."""
    if not is_mobile_phone(phone):
        logger.warning(f"[Evolution] Número no móvil ignorado: {phone}")
        return {"ok": False, "phone": phone, "error": "not_mobile", "skipped": True}
    number = _normalize_phone(phone)
    try:
        r = requests.post(
            f"{_base_url()}/message/sendMedia/{_instance()}",
            headers=_headers(),
            json={
                "number":  number,
                "options": {"delay": 1500, "presence": "composing"},
                "mediaMessage": {
                    "mediatype": "image",
                    "media":     image_url,
                    "caption":   caption,
                },
            },
            timeout=_timeout(),
        )
        data = r.json()
        ok = r.status_code < 300 and data.get("key") is not None
        if ok:
            logger.info(f"[Evolution] Imagen enviada → {number}")
        else:
            logger.warning(f"[Evolution] Fallo imagen → {number}: {data}")
        return {"ok": ok, "phone": number, "data": data, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[Evolution] Error enviando imagen a {number}: {e}")
        return {"ok": False, "phone": number, "error": str(e)}


def send_message(phone: str, message: str, image_url: Optional[str] = None) -> dict:
    """Wrapper unificado: con imagen o solo texto."""
    if image_url:
        result = send_image(phone, image_url, caption=message)
        if not result["ok"]:
            logger.warning(f"[Evolution] Imagen falló, reintentando solo texto → {phone}")
            result = send_text(phone, message)
    else:
        result = send_text(phone, message)
    return result


# ── WEBHOOK ──────────────────────────────────────────────────────
def set_webhook(webhook_url: str) -> dict:
    """Registra webhook para recibir mensajes entrantes."""
    try:
        r = requests.post(
            f"{_base_url()}/webhook/set/{_instance()}",
            headers=_headers(),
            json={
                "url":     webhook_url,
                "enabled": True,
                "events":  [
                    "MESSAGES_UPSERT",
                    "CONNECTION_UPDATE",
                    "MESSAGES_UPDATE",
                ],
            },
            timeout=_timeout(),
        )
        data = r.json()
        return {"ok": r.status_code < 300, "data": data}
    except Exception as e:
        logger.error(f"[Evolution] Error configurando webhook: {e}")
        return {"ok": False, "error": str(e)}


# ── HEALTH CHECK ─────────────────────────────────────────────────
def is_connected() -> bool:
    """True si la instancia está conectada y lista para enviar."""
    state = get_connection_state()
    return state.get("state") == "open"


def ensure_instance_exists() -> bool:
    """Crea la instancia si no existe. Retorna True si está lista."""
    try:
        state = get_connection_state()
        if state.get("state") in ("open", "connecting", "close"):
            return True
        # Si da 404 o error, crear
        result = create_instance()
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"[Evolution] Error en ensure_instance_exists: {e}")
        return False
