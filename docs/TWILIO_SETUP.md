# Twilio WhatsApp — Setup y activación

> Documento de configuración para integrar Twilio como backend WhatsApp del
> proyecto MP Prospecting. Reemplaza Evolution API una vez aprobado por IAM
> Media y Meta.

---

## ⚠️ Pre-requisitos institucionales (HACER ANTES DE TOCAR CÓDIGO)

Antes de configurar variables de entorno y enviar mensajes, hay que tener
**por escrito** de IAM Media (`iam_soporte_rrss@mercadolibre.com`):

- [ ] Confirmación de alcance: ¿mensajes proactivos a clientes externos sí/no?
- [ ] Proceso de aprobación de templates
- [ ] Responsabilidad operacional (a quién va el ticket si hay reclamos)
- [ ] Cost center / facturación de la cuenta Twilio

Y de tu lado:

- [ ] 2FA activado en tu cuenta Twilio (`console.twilio.com` → User Settings → Security)
- [ ] Número `+56 9 3510 3447` con status `Approved` en Meta Business Manager
- [ ] Acceso de lectura/escritura sobre el Phone Number SID correspondiente en Twilio

---

## 🔑 Variables de entorno requeridas

Cargás todas estas en Railway env vars (NO en el repo, NO en `.env` commiteado).

| Variable | Obligatoria | Descripción |
|---|---|---|
| `WA_BACKEND` | sí | `evolution` (default) o `twilio` · controla qué cliente usa el dispatcher |
| `TWILIO_ACCOUNT_SID` | sí | Account SID que empieza con `AC...` · público, pero por convención en env |
| `TWILIO_AUTH_TOKEN` | sí | **CRÍTICO** · llave maestra de la cuenta · jamás en código ni logs |
| `TWILIO_WHATSAPP_FROM` | sí | Número con prefijo: `whatsapp:+56935103447` |
| `TWILIO_MESSAGING_SID` | no | Messaging Service SID si se usa servicio agrupado |
| `TWILIO_TEST_WHITELIST` | recomendado | CSV de números autorizados para `/test-send` (anti-disparo accidental a clientes reales) |

### Dónde obtener cada valor en Twilio Console

1. **Account SID y Auth Token**
   - `console.twilio.com` → Página principal → Account Info (panel derecho)
   - Click en el icono de ojo para revelar el Auth Token
   - Copialo al gestor de contraseñas inmediatamente · no a archivos planos

2. **Phone Number / Sender**
   - `Develop` → `Messaging` → `Senders` → `WhatsApp senders`
   - Click en `Sebastian Pinto - Mercado Pago` (+56 9 3510 3447)
   - Tomar el número formateado y agregarle prefijo `whatsapp:`

3. **Messaging Service SID** (opcional)
   - `Develop` → `Messaging` → `Services`
   - Si existe uno asociado al número, usar su SID `MG...`

---

## 🚀 Activación paso a paso

### Paso 1 — Cargar credenciales en Railway

```
Railway dashboard → tu proyecto → Variables tab → New Variable
```

Cargá las 5-6 variables sin pegarlas en ningún chat ni screenshot:

```
WA_BACKEND=evolution           ← arrancamos así, NO activamos todavía
TWILIO_ACCOUNT_SID=AC...
TWILIO_AUTH_TOKEN=...
TWILIO_WHATSAPP_FROM=whatsapp:+56935103447
TWILIO_TEST_WHITELIST=56935103447,56999999999
```

Railway redeploya automáticamente al cambiar env vars. Confirma que el log
de arranque dice `Blueprint twilio registered`.

### Paso 2 — Verificar credenciales (sin enviar nada)

Desde el dashboard, abrí:

```
https://web-production-b6446.up.railway.app/api/twilio/health
```

Esperado:

```json
{
  "backend_active": false,
  "configured":     true,
  "health": {
    "ok":            true,
    "friendly_name": "...",
    "status":        "active",
    "type":          "Full"
  }
}
```

Si `configured=false` → falta alguna env var. Si `health.ok=false` →
las credenciales no son válidas.

### Paso 3 — Configurar webhook en Twilio Console

En Twilio Console:
1. `Develop` → `Messaging` → `Senders` → `WhatsApp senders`
2. Click en el sender `+56 9 3510 3447`
3. Sección `Webhook configuration`:
   - **A message comes in**: `POST` →
     `https://web-production-b6446.up.railway.app/api/twilio/webhook`
   - **Status callback URL**: (vacío por ahora)
4. Save

Importante: Twilio firma cada request con HMAC-SHA1 usando el Auth Token.
El endpoint `/api/twilio/webhook` valida la firma con
`hmac.compare_digest` antes de procesar. Sin firma válida → 403.

### Paso 4 — Test de envío a tu propio número (sandbox seguro)

Antes de activar Twilio como backend del bot, validá un envío manual a tu
propio teléfono (que debe estar en `TWILIO_TEST_WHITELIST`):

```bash
curl -X POST https://web-production-b6446.up.railway.app/api/twilio/test-send \
  -H "Content-Type: application/json" \
  -H "Cookie: session=..." \
  -d '{"phone": "56935103447", "message": "Test desde MP Prospecting"}'
```

Si llega el WhatsApp a tu teléfono, todo OK.

### Paso 5 — Activar Twilio como backend del bot

Solo cuando los pasos 1-4 estén verdes:

```
Railway → Variables → WA_BACKEND=twilio
```

A partir de ese momento, todos los mensajes entrantes son procesados por
el dispatcher usando Twilio. Evolution queda silenciado.

### Paso 6 — Switch de vuelta a Evolution (rollback)

Si algo falla:

```
Railway → Variables → WA_BACKEND=evolution
```

Cambio instantáneo, sin redeploy de código. El dispatcher vuelve a
Evolution.

---

## 🔒 Notas de seguridad

### Por qué el Auth Token es crítico
- Permite mandar mensajes con identidad **"Sebastian Pinto - Mercado Pago"**
  hacia cualquier número del mundo, con cargo a la cuenta corporativa MP
- Si se filtra:
  1. Rotar inmediatamente en Twilio Console (Account Info → Auth Token → Rotate)
  2. Actualizar env var en Railway
  3. Notificar a IAM Media del incidente

### Webhook signature validation
- Implementado en `whatsapp/twilio_client.py::validate_webhook_signature`
- Mitiga CWE-345 (Insufficient Verification of Data Authenticity)
- Sin validación, cualquiera podría inyectar mensajes falsos al dispatcher
  (ej. "BAJA" desde un número de cliente para forzar opt-out)

### PII en logs
- El cliente Twilio **no loguea body de mensajes** ni números completos
- Solo guarda hashes SHA-256 truncados (`_phone_hash`) y últimos 6 dígitos
- Mitigación de CWE-532 (Sensitive Information in Log File)

### Anti-disparo accidental
- `/api/twilio/test-send` solo permite envío a números en
  `TWILIO_TEST_WHITELIST`
- Sin whitelist o con destino fuera de ella → 400, no envía

### 2FA obligatorio
- La cuenta Twilio tiene capacidad de enviar mensajes con identidad MP
  corporativa. Operar sin 2FA es single-factor auth sobre un asset crítico
  (CWE-308).

---

## 📋 Endpoints expuestos

| Endpoint | Método | Auth | Descripción |
|---|---|---|---|
| `/api/twilio/webhook` | POST | Firma Twilio | Recepción de mensajes entrantes |
| `/api/twilio/health` | GET | Owner | Validación de credenciales |
| `/api/twilio/webhook-debug` | GET | Owner | Ring buffer últimos 50 webhooks |
| `/api/twilio/test-send` | POST | Owner | Envío a número whitelisted |

---

## 🆘 Troubleshooting

**Webhook devuelve 403 todo el tiempo:**
- Verificar `TWILIO_AUTH_TOKEN` correcto (último rotado)
- Verificar que Railway no esté removiendo el header `X-Twilio-Signature`
- Verificar que `X-Forwarded-Proto` y `X-Forwarded-Host` lleguen correctamente

**Mensajes no llegan al cliente:**
- Verificar status del sender en Twilio Console (Approved · Quality green)
- Si es un mensaje proactivo (vos iniciás): debe ser un template aprobado
- Si es respuesta dentro de ventana de 24h: puede ser texto libre

**`/api/twilio/health` retorna 401:**
- Credenciales mal cargadas en Railway env
- Token expirado o rotado · regenerar y actualizar env

---

*Última actualización: 2026-05-16 · Owner: J.S. Pinto*
