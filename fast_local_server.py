"""
Servidor local para ejecutar Fast Registro con playwright.
Lo expone Cloudflare Tunnel para que Railway lo invoque.

Uso:
    python fast_local_server.py

Por defecto escucha en http://localhost:5050
"""
import asyncio
import logging
import os
from flask import Flask, request, jsonify

# Importamos la función playwright existente
from routes.fast_registro import _registrar_en_fast

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger(__name__)

app = Flask(__name__)

# Token simple para que solo Railway pueda llamar a este endpoint
FAST_LOCAL_TOKEN = os.getenv("FAST_LOCAL_TOKEN", "cambiame-en-produccion")


@app.route("/health", methods=["GET"])
def health():
    return jsonify({"ok": True, "service": "fast-local"})


@app.route("/registrar-fast", methods=["POST"])
def registrar_fast():
    # Validar token
    auth = request.headers.get("X-Fast-Token", "")
    if auth != FAST_LOCAL_TOKEN:
        logger.warning(f"[Fast Local] Token inválido: {auth[:10]}...")
        return jsonify({"ok": False, "mensaje": "Unauthorized"}), 401

    data = request.get_json() or {}
    nombre = (data.get("nombre") or "").strip()
    telefono = (data.get("telefono") or "").strip()
    direccion = (data.get("direccion") or "").strip()

    if not nombre or not telefono:
        return jsonify({"ok": False, "mensaje": "nombre y telefono requeridos"}), 400

    logger.info(f"[Fast Local] Registrando: {nombre} ({telefono})")

    # Ejecutar playwright en un loop dedicado
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        result = loop.run_until_complete(
            _registrar_en_fast(nombre, telefono, direccion)
        )
    except Exception as e:
        logger.error(f"[Fast Local] Error: {e}", exc_info=True)
        result = {"ok": False, "mensaje": f"Error local: {str(e)[:200]}"}
    finally:
        loop.close()
        asyncio.set_event_loop(None)

    logger.info(f"[Fast Local] Resultado: {result}")
    return jsonify(result)


if __name__ == "__main__":
    port = int(os.getenv("FAST_LOCAL_PORT", 5050))
    print(f"\n=== Fast Local Server ===")
    print(f"Escuchando en http://localhost:{port}")
    print(f"Token actual: {FAST_LOCAL_TOKEN}")
    print(f"Para Cloudflare Tunnel: cloudflared tunnel --url http://localhost:{port}\n")
    app.run(host="0.0.0.0", port=port, debug=False)
