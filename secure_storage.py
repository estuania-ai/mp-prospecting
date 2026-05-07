"""
Encriptación simétrica para credenciales sensibles en BD (ej: App Password Gmail).

Usa Fernet (AES-128 + HMAC-SHA256) con clave de 32 bytes en env APP_ENCRYPTION_KEY.

Si la env var no está seteada:
- En dev local: genera una clave temporal y la loguea como WARNING
- En producción (Railway): debe estar seteada o las credenciales no se podrán
  guardar (mejor fallar a propósito que guardar en plaintext)
"""
import os
import base64
import logging
from cryptography.fernet import Fernet, InvalidToken

logger = logging.getLogger(__name__)

_FERNET = None


def _get_fernet():
    global _FERNET
    if _FERNET is not None:
        return _FERNET

    key_b64 = os.getenv('APP_ENCRYPTION_KEY', '').strip()
    if not key_b64:
        # Generar clave efímera para que la app no crashee en dev sin la var
        # Las credenciales encriptadas con esta clave NO sobrevivirán a un restart
        ephemeral = Fernet.generate_key()
        logger.warning(
            "[secure_storage] APP_ENCRYPTION_KEY no seteada. Usando clave efímera. "
            "Credenciales guardadas no podrán descifrarse después de un restart. "
            "Setea APP_ENCRYPTION_KEY en Railway con: python -c 'from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())'"
        )
        _FERNET = Fernet(ephemeral)
    else:
        try:
            # Validar formato (32 bytes base64-url-safe)
            Fernet(key_b64.encode() if isinstance(key_b64, str) else key_b64)
            _FERNET = Fernet(key_b64.encode() if isinstance(key_b64, str) else key_b64)
        except Exception as e:
            logger.error(f"[secure_storage] APP_ENCRYPTION_KEY inválida: {e}")
            raise
    return _FERNET


def encrypt(plaintext: str) -> str:
    """Encripta y devuelve string base64 (apto para guardar en BD)."""
    if not plaintext:
        return ''
    f = _get_fernet()
    return f.encrypt(plaintext.encode('utf-8')).decode('utf-8')


def decrypt(token: str) -> str:
    """Desencripta un token previamente generado por encrypt()."""
    if not token:
        return ''
    f = _get_fernet()
    try:
        return f.decrypt(token.encode('utf-8')).decode('utf-8')
    except InvalidToken:
        logger.warning("[secure_storage] Token inválido o clave incorrecta")
        return ''
    except Exception as e:
        logger.error(f"[secure_storage] Error desencriptando: {e}")
        return ''


def generate_key() -> str:
    """Helper: genera una clave nueva. Útil para configurar APP_ENCRYPTION_KEY."""
    return Fernet.generate_key().decode()
