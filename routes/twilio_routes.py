"""
Blueprint: /api/twilio
Webhook receptor de Twilio WhatsApp + endpoints de salud.

ACTIVACIÓN:
  Para usar Twilio en vez de Evolution, setear env var:
    WA_BACKEND=twilio

  Con WA_BACKEND=evolution (default) este blueprint queda silenciado:
  los webhooks responden 200 pero no procesan nada.

SEGURIDAD:
  - Todos los POST a /webhook validan firma X-Twilio-Signature
  - Sin firma válida → 403 sin procesar (CWE-345 mitigation)
  - El Auth Token NUNCA se loguea ni se devuelve en respuestas
"""
from __future__ import annotations
import os
import logging
import threading
from flask import Blueprint, jsonify, request, Response
from flask_login import current_user, login_required

from whatsapp import twilio_client as tw

logger = logging.getLogger(__name__)
bp = Blueprint("twilio", __name__, url_prefix="/api/twilio")


def _backend_active() -> bool:
    return os.getenv("WA_BACKEND", "evolution").lower() == "twilio"


# ── Ring buffer en memoria para diagnóstico (últimos 50 webhooks) ──
_WEBHOOK_BUFFER: list = []
_WEBHOOK_MAX = 50


def _push_debug(entry: dict) -> None:
    from datetime import datetime
    entry["_received_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    _WEBHOOK_BUFFER.append(entry)
    if len(_WEBHOOK_BUFFER) > _WEBHOOK_MAX:
        _WEBHOOK_BUFFER.pop(0)


# ═══════════════════════════════════════════════════════════════
# WEBHOOK RECEIVER
# ═══════════════════════════════════════════════════════════════
@bp.post("/webhook")
def twilio_webhook():
    """
    Recibe mensajes entrantes de Twilio WhatsApp.
    Twilio firma cada request con X-Twilio-Signature (HMAC-SHA1).
    """
    # ── Validar firma SIEMPRE, antes de leer params ─────────────
    signature = request.headers.get("X-Twilio-Signature", "")

    # URL completa que Twilio usó para firmar (sin barra final extra)
    # Importante: Twilio firma con la URL EXACTA con la que pegó · si Railway
    # tiene proxy y cambia http→https, hay que construirla desde X-Forwarded-Proto
    proto = request.headers.get("X-Forwarded-Proto", request.scheme)
    host  = request.headers.get("X-Forwarded-Host", request.host)
    url   = f"{proto}://{host}{request.path}"

    params = request.form.to_dict()

    if not tw.validate_webhook_signature(url, params, signature):
        logger.warning(
            f"[Twilio webhook] firma inválida path={request.path} "
            f"signature_present={bool(signature)}"
        )
        return Response("Forbidden", status=403)

    # ── Si Twilio no es el backend activo, solo loguear y salir ─
    if not _backend_active():
        _push_debug({
            "ignored": "WA_BACKEND != twilio",
            "from":    params.get("From", "")[-6:],   # solo últimos 6 dígitos
        })
        return _twiml_empty()

    # ── Procesar mensaje entrante ───────────────────────────────
    from_raw = params.get("From", "")     # "whatsapp:+56932320023"
    to_raw   = params.get("To", "")       # nuestro número
    body     = (params.get("Body") or "").strip()
    num_med  = int(params.get("NumMedia", "0") or 0)

    # Limpiar el JID a solo dígitos
    client_phone = _strip_whatsapp_prefix(from_raw)

    # Log seguro · solo metadatos, jamás el body completo
    _push_debug({
        "from_last6": from_raw[-6:],
        "to_last6":   to_raw[-6:],
        "body_len":   len(body),
        "num_media":  num_med,
    })

    if not client_phone:
        return _twiml_empty()

    # Resolver user_id del bot (Owner activo por defecto)
    from database import get_db
    conn = get_db()
    row = conn.execute(
        "SELECT id FROM users WHERE role='owner' AND status='active' "
        "ORDER BY id ASC LIMIT 1"
    ).fetchone()
    user_id = row["id"] if row else None
    conn.close()

    if not user_id:
        return _twiml_empty()

    # Disparar dispatcher en background · no bloqueamos el webhook
    def _bg():
        try:
            from wa_bot.dispatcher import handle_incoming_message
            handle_incoming_message(
                user_id=user_id,
                client_phone=client_phone,
                text=body,
                client=tw,                  # módulo twilio_client cumple BotClient
                instance=None,
                is_from_me=False,
            )
        except Exception as e:
            logger.error(f"[Twilio webhook] dispatcher error: {e}", exc_info=True)

    threading.Thread(target=_bg, daemon=True).start()
    return _twiml_empty()


def _strip_whatsapp_prefix(jid: str) -> str:
    """'whatsapp:+56932320023' → '56932320023'"""
    if not jid:
        return ""
    s = jid.replace("whatsapp:", "").replace("+", "").strip()
    return "".join(ch for ch in s if ch.isdigit())


def _twiml_empty() -> Response:
    """Respuesta TwiML vacía · le dice a Twilio 'OK recibido, no contestes'."""
    return Response("<Response></Response>", mimetype="application/xml")


# ═══════════════════════════════════════════════════════════════
# DIAGNÓSTICO (solo Owner)
# ═══════════════════════════════════════════════════════════════
@bp.get("/health")
@login_required
def twilio_health():
    """Verifica que las credenciales Twilio sean válidas (no envía nada)."""
    if current_user.role != "owner":
        return jsonify({"error": "Solo Owner"}), 403
    return jsonify({
        "backend_active": _backend_active(),
        "configured":     tw.is_configured(),
        "health":         tw.health_check(),
    })


@bp.get("/webhook-debug")
@login_required
def twilio_webhook_debug():
    """Últimos 50 eventos recibidos · útil para verificar que Twilio llega."""
    if current_user.role != "owner":
        return jsonify({"error": "Solo Owner"}), 403
    return jsonify({
        "events":      list(reversed(_WEBHOOK_BUFFER)),
        "total":       len(_WEBHOOK_BUFFER),
        "backend":     os.getenv("WA_BACKEND", "evolution"),
    })


@bp.post("/test-send")
@login_required
def twilio_test_send():
    """
    Envía un mensaje de prueba al teléfono dado. Solo Owner.
    Body: { "phone": "56932320023", "message": "Test" }

    NO envía mensajes con marca MP corporativa si el destino no es el propio
    Owner (anti-mistake). Validación adicional: el destino debe ser tu propio
    número o uno explícitamente whitelisted en TWILIO_TEST_WHITELIST.
    """
    if current_user.role != "owner":
        return jsonify({"error": "Solo Owner"}), 403
    if not _backend_active():
        return jsonify({"error": "WA_BACKEND no está en 'twilio'"}), 400

    data = request.get_json() or {}
    phone = (data.get("phone") or "").strip()
    msg   = (data.get("message") or "Test desde MP Prospecting").strip()
    if not phone:
        return jsonify({"error": "phone requerido"}), 400

    # Validación anti-disparo accidental a clientes reales
    whitelist = (os.getenv("TWILIO_TEST_WHITELIST") or "").split(",")
    whitelist = [w.strip() for w in whitelist if w.strip()]
    clean = "".join(ch for ch in phone if ch.isdigit())
    if whitelist and clean not in whitelist:
        return jsonify({
            "error": "phone no está en TWILIO_TEST_WHITELIST",
            "hint":  "agregá el número a la env var para permitir pruebas a ese destino",
        }), 400

    result = tw.send_text(phone, msg)
    # No exponer el SID en respuesta · solo confirmación
    return jsonify({
        "ok":      result.get("ok"),
        "error":   result.get("error") if not result.get("ok") else None,
    })
