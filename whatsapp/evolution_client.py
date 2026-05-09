"""
Evolution API Client — soporta multi-instancia (una por usuario/Sales).

Cada función acepta un parámetro `instance` opcional. Si no se pasa,
se usa la variable de entorno EVOLUTION_INSTANCE (instancia "owner"/legacy).
Esto permite que el Owner siga usando su instancia actual y cada Sales
tenga la suya con su propio QR.

Configuración en .env:
  EVOLUTION_API_URL=http://localhost:8080
  EVOLUTION_API_KEY=tu_api_key
  EVOLUTION_INSTANCE=mp_prospecting          (instancia legacy/owner)
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

def _default_instance() -> str:
    return os.getenv('EVOLUTION_INSTANCE', 'mp_prospecting')

def _resolve_instance(instance: Optional[str]) -> str:
    return instance.strip() if (instance and instance.strip()) else _default_instance()

def _headers() -> dict:
    return {
        'apikey': _api_key(),
        'Content-Type': 'application/json',
    }

def _timeout() -> int:
    return 20


# ── INSTANCIA ────────────────────────────────────────────────────
def create_instance(instance: Optional[str] = None) -> dict:
    """Crea la instancia en Evolution API (idempotente: si ya existe, no falla)."""
    inst = _resolve_instance(instance)
    try:
        r = requests.post(
            f"{_base_url()}/instance/create",
            headers=_headers(),
            json={
                "instanceName": inst,
                "token":        _api_key(),
                "qrcode":       True,
                "integration":  "WHATSAPP-BAILEYS",
            },
            timeout=_timeout(),
        )
        data = r.json() if r.content else {}
        logger.info(f"[Evolution] create_instance({inst}): status={r.status_code}")
        # 201/200 = creada; 403 con "already in use" = ya existe (ok)
        if r.status_code >= 400:
            msg = str(data).lower()
            if 'already' in msg or 'exists' in msg or 'in use' in msg:
                return {"ok": True, "data": data, "already_exists": True}
            return {"ok": False, "data": data, "status": r.status_code}
        return {"ok": True, "data": data}
    except Exception as e:
        logger.error(f"[Evolution] Error creando instancia {inst}: {e}")
        return {"ok": False, "error": str(e)}


def get_connection_state(instance: Optional[str] = None) -> dict:
    """Retorna el estado de conexión: open / connecting / close."""
    inst = _resolve_instance(instance)
    try:
        r = requests.get(
            f"{_base_url()}/instance/connectionState/{inst}",
            headers=_headers(),
            timeout=_timeout(),
        )
        data = r.json() if r.content else {}
        if r.status_code == 404:
            return {"ok": True, "state": "not_found", "raw": data}
        state = data.get("instance", {}).get("state", "unknown")
        return {"ok": True, "state": state, "raw": data}
    except Exception as e:
        logger.error(f"[Evolution] Error obteniendo estado {inst}: {e}")
        return {"ok": False, "state": "error", "error": str(e)}


def get_qr_code(instance: Optional[str] = None) -> dict:
    """Obtiene el QR code para escanear (base64 PNG). Si la instancia
    no existe, la crea primero."""
    inst = _resolve_instance(instance)
    # Asegurar que exista
    state = get_connection_state(inst)
    if state.get("state") == "not_found":
        create_instance(inst)
    try:
        r = requests.get(
            f"{_base_url()}/instance/connect/{inst}",
            headers=_headers(),
            timeout=_timeout(),
        )
        data = r.json() if r.content else {}
        qr_base64 = (
            data.get("base64")
            or data.get("qrcode", {}).get("base64")
            or data.get("code")
        )
        return {"ok": True, "qr": qr_base64, "raw": data}
    except Exception as e:
        logger.error(f"[Evolution] Error obteniendo QR {inst}: {e}")
        return {"ok": False, "error": str(e)}


def logout_instance(instance: Optional[str] = None) -> dict:
    """Desconecta la instancia (cierra sesión WhatsApp)."""
    inst = _resolve_instance(instance)
    try:
        r = requests.delete(
            f"{_base_url()}/instance/logout/{inst}",
            headers=_headers(),
            timeout=_timeout(),
        )
        return {"ok": r.status_code < 300}
    except Exception as e:
        logger.error(f"[Evolution] Error desconectando {inst}: {e}")
        return {"ok": False, "error": str(e)}


def restart_instance(instance: Optional[str] = None) -> dict:
    """Reinicia la instancia (útil si se cuelga)."""
    inst = _resolve_instance(instance)
    try:
        r = requests.put(
            f"{_base_url()}/instance/restart/{inst}",
            headers=_headers(),
            timeout=_timeout(),
        )
        return {"ok": r.status_code < 300}
    except Exception as e:
        logger.error(f"[Evolution] Error reiniciando {inst}: {e}")
        return {"ok": False, "error": str(e)}


def delete_instance(instance: Optional[str] = None) -> dict:
    """Borra completamente la instancia (require confirmación del usuario)."""
    inst = _resolve_instance(instance)
    try:
        r = requests.delete(
            f"{_base_url()}/instance/delete/{inst}",
            headers=_headers(),
            timeout=_timeout(),
        )
        return {"ok": r.status_code < 300}
    except Exception as e:
        logger.error(f"[Evolution] Error borrando {inst}: {e}")
        return {"ok": False, "error": str(e)}


# ── ENVÍO DE MENSAJES ────────────────────────────────────────────
def _normalize_phone(phone: str) -> str:
    digits = ''.join(filter(str.isdigit, phone))
    if digits.startswith('0'):
        digits = digits[1:]
    if len(digits) == 9 and not digits.startswith('56'):
        digits = '56' + digits
    return digits


def is_mobile_phone(phone: str) -> bool:
    digits = _normalize_phone(phone)
    return digits.startswith('569') and len(digits) == 11


def send_text(phone: str, message: str, instance: Optional[str] = None) -> dict:
    inst = _resolve_instance(instance)
    number = _normalize_phone(phone)
    if not is_mobile_phone(phone):
        logger.warning(f"[Evolution {inst}] Número no móvil ignorado: {number}")
        return {"ok": False, "phone": number, "error": "not_mobile", "skipped": True}
    try:
        r = requests.post(
            f"{_base_url()}/message/sendText/{inst}",
            headers=_headers(),
            json={
                "number":  number,
                "options": {"delay": 1500, "presence": "composing"},
                "textMessage": {"text": message},
            },
            timeout=_timeout(),
        )
        data = r.json() if r.content else {}
        ok = r.status_code < 300 and data.get("key") is not None
        if ok:
            logger.info(f"[Evolution {inst}] Texto enviado → {number}")
        else:
            logger.warning(f"[Evolution {inst}] Fallo texto → {number}: {data}")
        return {"ok": ok, "phone": number, "data": data, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[Evolution {inst}] Error enviando texto a {number}: {e}")
        return {"ok": False, "phone": number, "error": str(e)}


def send_image(phone: str, image_url: str, caption: str = "", instance: Optional[str] = None) -> dict:
    inst = _resolve_instance(instance)
    if not is_mobile_phone(phone):
        logger.warning(f"[Evolution {inst}] Número no móvil ignorado: {phone}")
        return {"ok": False, "phone": phone, "error": "not_mobile", "skipped": True}
    number = _normalize_phone(phone)
    try:
        r = requests.post(
            f"{_base_url()}/message/sendMedia/{inst}",
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
        data = r.json() if r.content else {}
        ok = r.status_code < 300 and data.get("key") is not None
        if ok:
            logger.info(f"[Evolution {inst}] Imagen enviada → {number}")
        else:
            logger.warning(f"[Evolution {inst}] Fallo imagen → {number}: {data}")
        return {"ok": ok, "phone": number, "data": data, "timestamp": datetime.now().isoformat()}
    except Exception as e:
        logger.error(f"[Evolution {inst}] Error enviando imagen a {number}: {e}")
        return {"ok": False, "phone": number, "error": str(e)}


def send_message(phone: str, message: str, image_url: Optional[str] = None,
                 instance: Optional[str] = None) -> dict:
    """Wrapper unificado: con imagen o solo texto. Acepta `instance` per-user."""
    if image_url:
        result = send_image(phone, image_url, caption=message, instance=instance)
        if not result["ok"]:
            logger.warning(f"[Evolution] Imagen falló, reintentando solo texto → {phone}")
            result = send_text(phone, message, instance=instance)
    else:
        result = send_text(phone, message, instance=instance)
    return result


# ── WEBHOOK ──────────────────────────────────────────────────────
def set_webhook(webhook_url: str, instance: Optional[str] = None) -> dict:
    """
    Configura el webhook de la instancia. Intenta varios formatos de payload
    porque Evolution cambió la shape entre v1 / v2.0 / v2.1+:
      - v2.1: {"webhook": {url, enabled, events, webhookByEvents, webhookBase64}}
      - v2.0: {"webhook": {url, enabled, events, byEvents, base64}}
      - v1:   {url, enabled, events}
    Eventos en SCREAMING_SNAKE; v2 también acepta dotted lowercase pero queda
    documentado lo primero. Probamos todos hasta que uno responda 2xx + setee
    los events. Devuelve el response crudo del primero que aceptó.
    """
    inst = _resolve_instance(instance)
    events = [
        "MESSAGES_UPSERT",
        "CONNECTION_UPDATE",
        "MESSAGES_UPDATE",
    ]
    url = f"{_base_url()}/webhook/set/{inst}"

    # Evolution v2 (flat camelCase) — confirmado por response {"ok":true,"webhook":null}
    # cuando se manda el body anidado: el server acepta el JSON pero no encuentra
    # los campos en el shape esperado y guarda un webhook vacío.
    body_v2_flat = {
        "enabled":         True,
        "url":             webhook_url,
        "events":          events,
        "webhookByEvents": False,
        "webhookBase64":   False,
    }
    # Evolution v2 (anidado, algunas versiones intermedias lo aceptan)
    body_v2_nested = {
        "webhook": {
            "enabled":         True,
            "url":             webhook_url,
            "events":          events,
            "webhookByEvents": False,
            "webhookBase64":   False,
        }
    }
    # v1 plano legacy
    body_v1 = {
        "url":     webhook_url,
        "enabled": True,
        "events":  events,
    }

    attempts = []
    for label, body in (
        ("v2-flat",   body_v2_flat),
        ("v2-nested", body_v2_nested),
        ("v1",        body_v1),
    ):
        try:
            r = requests.post(url, headers=_headers(), json=body, timeout=_timeout())
            try:
                data = r.json() if r.content else {}
            except Exception:
                data = {"_raw": r.text[:300]}
            attempt = {
                "format": label,
                "status": r.status_code,
                "body":   data,
            }
            attempts.append(attempt)
            # Evolution v2 puede responder 200 + {"ok":true,"webhook":null} cuando
            # ignora el body por shape incorrecta. Validamos que efectivamente
            # haya guardado la URL antes de aceptar.
            if r.status_code < 300:
                wh = data.get("webhook") if isinstance(data, dict) else None
                saved_url = (
                    (wh or {}).get("url") if isinstance(wh, dict)
                    else (data.get("url") if isinstance(data, dict) else None)
                )
                if saved_url == webhook_url or (wh and wh != {} and wh is not None):
                    logger.info(f"[Evolution {inst}] webhook set OK formato {label}: {data}")
                    return {
                        "ok":       True,
                        "format":   label,
                        "data":     data,
                        "attempts": attempts,
                    }
                logger.warning(
                    f"[Evolution {inst}] webhook {label} 200 pero NO persistido (webhook={wh}); probando siguiente"
                )
            logger.warning(
                f"[Evolution {inst}] webhook {label} status={r.status_code} body={r.text[:200]}"
            )
        except Exception as e:
            attempts.append({"format": label, "exception": str(e)})
            logger.warning(f"[Evolution {inst}] webhook {label} exc: {e}")
    return {"ok": False, "error": "Todos los formatos fallaron", "attempts": attempts}


# ── HEALTH CHECK ─────────────────────────────────────────────────
def is_connected(instance: Optional[str] = None) -> bool:
    """True si la instancia está conectada y lista para enviar."""
    state = get_connection_state(instance)
    return state.get("state") == "open"


def ensure_instance_exists(instance: Optional[str] = None) -> bool:
    """Crea la instancia si no existe. Retorna True si está lista (no necesariamente conectada)."""
    try:
        state = get_connection_state(instance)
        if state.get("state") in ("open", "connecting", "close"):
            return True
        if state.get("state") == "not_found":
            result = create_instance(instance)
            return result.get("ok", False)
        # Caso "unknown"/"error" — intentamos crear igual
        result = create_instance(instance)
        return result.get("ok", False)
    except Exception as e:
        logger.error(f"[Evolution] Error en ensure_instance_exists: {e}")
        return False


# ── HELPERS PER-USER ─────────────────────────────────────────────
def instance_name_for_user(user_id: int, role: str = '') -> str:
    """
    Genera nombre de instancia determinístico por usuario.
    - Owner usa la instancia legacy (env EVOLUTION_INSTANCE) para no romper
      nada existente.
    - Sales/TL usan 'sales_<id>'.
    """
    if role == 'owner':
        return _default_instance()
    return f"sales_{int(user_id)}"
