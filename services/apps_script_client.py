"""
Cliente HTTP para el Apps Script Web App que crea borradores Gmail.

Endpoint deployado en la cuenta Gmail del Owner (Apps Script Web App).
La URL y el shared secret vienen de env vars:
  APPS_SCRIPT_DRAFTS_URL       · URL del deployment (https://script.google.com/...)
  APPS_SCRIPT_SHARED_SECRET    · string random largo · debe coincidir con el
                                 Script Property SHARED_SECRET del Apps Script

Ver docs/APPS_SCRIPT_DRAFTS.md para el paso a paso de deploy.

Seguridad incorporada:
  · Payload máximo 100 drafts · límite protegido en el cliente Y en el Apps Script
  · Shared secret validado en ambos lados (evita que URL filtrada = drafts abiertos)
  · Timeout 60s · evita cuelgues si Apps Script se enlentece
  · No loguea ni el secret ni el HTML completo (solo métricas)
"""
from __future__ import annotations
import logging
import os
from typing import Optional
import requests

logger = logging.getLogger(__name__)

# Constantes de protección
MAX_DRAFTS_PER_REQUEST = 100
REQUEST_TIMEOUT_SECONDS = 60


class AppsScriptError(Exception):
    """Excepción específica para fallos del cliente Apps Script."""


def _get_config() -> tuple[str, str]:
    """
    Recupera URL y secret de env vars. Falla explícito si faltan.
    """
    url = (os.getenv("APPS_SCRIPT_DRAFTS_URL") or "").strip()
    secret = (os.getenv("APPS_SCRIPT_SHARED_SECRET") or "").strip()
    if not url:
        raise AppsScriptError("APPS_SCRIPT_DRAFTS_URL no configurada")
    if not secret:
        raise AppsScriptError("APPS_SCRIPT_SHARED_SECRET no configurada")
    if len(secret) < 16:
        raise AppsScriptError("APPS_SCRIPT_SHARED_SECRET muy corto (mín 16 chars)")
    if not url.startswith("https://"):
        raise AppsScriptError("APPS_SCRIPT_DRAFTS_URL debe ser HTTPS")
    return url, secret


def create_drafts(drafts: list[dict], sender_name: str = "Juan Sebastián Pinto") -> dict:
    """
    Envía la lista de drafts al Apps Script para crearlos en Gmail.

    Cada draft debe tener:
      · to        · email destino
      · subject   · asunto
      · htmlBody  · cuerpo HTML ya renderizado (Jinja2 hecho antes)

    Retorna dict con:
      · created  · cuántos se crearon exitosamente
      · failed   · cuántos fallaron
      · results  · lista con draftId por cada uno
      · errors   · lista con {index, to, error} de los que fallaron
      · gmail_drafts_url · URL directa a los borradores de Gmail
    """
    if not drafts:
        raise AppsScriptError("Lista de drafts vacía")
    if not isinstance(drafts, list):
        raise AppsScriptError("drafts debe ser una lista")
    if len(drafts) > MAX_DRAFTS_PER_REQUEST:
        raise AppsScriptError(
            f"Máximo {MAX_DRAFTS_PER_REQUEST} drafts por request (recibí {len(drafts)})"
        )

    # Validar shape de cada draft (fail-fast antes de tocar red)
    for i, d in enumerate(drafts):
        if not isinstance(d, dict):
            raise AppsScriptError(f"drafts[{i}] no es dict")
        if not d.get("to"):
            raise AppsScriptError(f"drafts[{i}] sin 'to'")
        if not d.get("subject"):
            raise AppsScriptError(f"drafts[{i}] sin 'subject'")
        if not d.get("htmlBody"):
            raise AppsScriptError(f"drafts[{i}] sin 'htmlBody'")

    url, secret = _get_config()

    payload = {
        "secret":     secret,
        "drafts":     drafts,
        "senderName": sender_name,
    }

    try:
        r = requests.post(
            url,
            json=payload,
            timeout=REQUEST_TIMEOUT_SECONDS,
            headers={"Content-Type": "application/json"},
        )
    except requests.Timeout:
        raise AppsScriptError(
            f"Timeout después de {REQUEST_TIMEOUT_SECONDS}s · Apps Script no respondió"
        )
    except requests.RequestException as e:
        raise AppsScriptError(f"Error de red al llamar Apps Script: {type(e).__name__}")

    if r.status_code >= 400:
        # NUNCA loguear el body completo · puede contener eco del secret o HTML
        logger.warning(
            "Apps Script respondió %s · body_len=%d",
            r.status_code, len(r.text or ""),
        )
        raise AppsScriptError(f"Apps Script status {r.status_code}")

    try:
        data = r.json()
    except ValueError:
        raise AppsScriptError("Apps Script devolvió respuesta no-JSON")

    if not data.get("ok"):
        err = str(data.get("error", "unknown"))[:200]
        raise AppsScriptError(f"Apps Script error: {err}")

    logger.info(
        "[apps_script] batch creado · created=%s failed=%s",
        data.get("created"), data.get("failed"),
    )
    return data


def health_check() -> dict:
    """
    Ping simple al Apps Script (envía payload mínimo inválido para probar
    conectividad + validación del shared secret sin crear drafts reales).

    Retorna: { url_ok, secret_ok, reachable, message }
    """
    result = {
        "url_ok":    False,
        "secret_ok": False,
        "reachable": False,
        "message":   "",
    }
    try:
        url, secret = _get_config()
        result["url_ok"] = True
        result["secret_ok"] = True
    except AppsScriptError as e:
        result["message"] = str(e)
        return result

    # Enviar payload con drafts vacío · Apps Script debe rechazar con 400
    # pero eso confirma que la URL responde y el secret es válido.
    try:
        r = requests.post(
            url,
            json={"secret": secret, "drafts": []},
            timeout=15,
            headers={"Content-Type": "application/json"},
        )
        result["reachable"] = True
        if r.status_code == 400 and "drafts" in (r.text or "").lower():
            result["message"] = "OK · Apps Script accesible y secret válido"
        elif r.status_code == 403:
            result["secret_ok"] = False
            result["message"] = "Secret rechazado por Apps Script (403)"
        else:
            result["message"] = f"Respuesta inesperada · status {r.status_code}"
    except Exception as e:
        result["message"] = f"No se pudo alcanzar el Apps Script: {type(e).__name__}"
    return result
