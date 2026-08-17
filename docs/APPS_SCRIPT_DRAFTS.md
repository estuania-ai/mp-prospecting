# Apps Script Drafts · Generación semi-automática de borradores Gmail

> Guía operativa para generar borradores personalizados desde el dashboard
> hacia tu Gmail corporativo, sin necesidad de API Gmail formal.
> Owner: Juan Sebastián Pinto · 2026-08-17

---

## ¿Qué resuelve esto?

Mientras espera la aprobación del OAuth Client ID para Gmail API (ver
`docs/ARCHITECTURE.md` y el ticket en curso con el equipo Cloud GCP),
el proyecto necesita seguir operando el envío de emails de prospección.

Este módulo permite:

1. **Filtrar contactos** desde el dashboard (por rubro, comuna, estado)
2. **Renderear el HTML personalizado** por cada contacto usando los
   templates existentes en `et_rubro_templates`
3. **Enviar el payload a un Apps Script** deployado en la cuenta Gmail
   del operador
4. **Apps Script crea borradores** con `GmailApp.createDraft()`
5. **El operador revisa y envía** manualmente desde su Gmail

**Beneficios clave:**

- ✅ Cero envío automático · vos tenés el control final
- ✅ No requiere aprobación OAuth · Apps Script corre con tus permisos
- ✅ Funciona local o en cualquier host · el destino es HTTPS de Google
- ✅ La responsabilidad legal del envío queda a tu nombre (sos vos quien envía)
- ✅ Fácil de desactivar · borrás el Apps Script y listo

---

## Arquitectura

```
┌─────────────────────┐                   ┌───────────────────────┐
│ Dashboard Flask     │  1. POST payload  │ Apps Script Web App   │
│ (localhost o Fury)  │─────────────────► │ (cuenta Gmail Owner)  │
│                     │  contacts + HTML  │                       │
│ - Selecciona leads  │  + shared_secret  │  GmailApp.            │
│ - Renderea Jinja2   │                   │  createDraft()        │
│ - POSTea            │◄──────────────────│                       │
└─────────────────────┘  2. draft IDs     └───────────┬───────────┘
         │                                            │
         ▼                                            ▼
    email_draft_batches                       Borradores en tu
    tabla persistente                         Gmail personal
                                              (juansebastian.pinto@
                                               mercadolibre.cl)
```

---

## Setup local del dashboard

Si estás corriendo el dashboard en tu PC (recomendado hasta que la
migración a Fury esté lista), seguí estos pasos:

### 1. Clonar y crear entorno virtual

```powershell
git clone https://github.com/estuania-ai/mp-prospecting.git
cd mp-prospecting
python -m venv .venv
.venv\Scripts\activate
pip install -r requirements.txt
```

### 2. Crear `.env` local

Copiá tu `.env` de Railway (variables de entorno) a un archivo `.env`
en la raíz del proyecto. **Agregá estas dos variables extra:**

```env
# Deshabilitar scheduler en local para NO disparar jobs reales
DISABLE_SCHEDULER=1

# Apps Script Drafts · llenar tras deployar el Apps Script
APPS_SCRIPT_DRAFTS_URL=
APPS_SCRIPT_SHARED_SECRET=
```

> **⚠️ Importante:** con `DISABLE_SCHEDULER=1` los 12 cron jobs NO se
> registran. El dashboard funciona igual, solo no se disparan envíos
> automáticos. Esencial cuando corrés local con credenciales productivas.

### 3. Levantar Flask local

```powershell
python app.py
```

Abrí `http://localhost:5000` en tu navegador.

Deberías ver en los logs:
```
[WARNING] SCHEDULER DESHABILITADO por DISABLE_SCHEDULER=1 · los jobs NO se van a ejecutar
```

Si aparece eso, listo.

---

## Deploy del Apps Script

### Paso 1 · Crear proyecto

1. Andá a [script.google.com](https://script.google.com) logueado
   con `juansebastian.pinto@mercadolibre.cl`
2. Click **New project**
3. Nombre: `MP Prospecting Drafts`
4. Borrá el código default de `Code.gs` y pegá el código completo
   que está al final de este documento (sección "Código completo")

### Paso 2 · Configurar shared secret

El shared secret protege el endpoint · sin él, cualquiera que descubra
la URL del Web App podría crear borradores en tu Gmail.

1. En el editor del Apps Script → icono ⚙️ **Project Settings** (izquierda)
2. Bajá hasta **Script Properties**
3. Click **Add script property**:
   - **Property:** `SHARED_SECRET`
   - **Value:** un string aleatorio de 32+ caracteres

Podés generar uno con:

```powershell
python -c "import secrets; print(secrets.token_urlsafe(32))"
```

O si preferís, en cualquier terminal Linux/Mac:

```bash
openssl rand -base64 32
```

**GUARDÁ ese secret en un gestor de contraseñas (Bitwarden, 1Password,
Keychain).** Lo vas a necesitar en el `.env` del dashboard.

### Paso 3 · Autorizar permisos Gmail

Antes del primer deploy, corré una función manual para autorizar:

1. En el dropdown de arriba, seleccioná `testCreateDraft`
2. Click **Run** (icono ▶️)
3. Google te va a pedir autorización · aceptás
4. Confirmá los permisos: `Send email as you` y `Create drafts`
5. Cuando termine, andá a Gmail y verificá que apareció un draft de test

Si el draft apareció, la autorización quedó lista.

### Paso 4 · Deploy como Web App

1. Arriba a la derecha: **Deploy → New deployment**
2. Icono ⚙️ → **Web app**
3. Configuración:
   - **Description:** `MP Prospecting drafts v1`
   - **Execute as:** **Me** (juansebastian.pinto@mercadolibre.cl)
   - **Who has access:** **Anyone**
     (⚠️ requerido para llamadas desde Flask · el shared secret hace la
     autenticación real · no exponemos ningún dato hasta validar secret)
4. Click **Deploy**
5. Copiá la **Web app URL** (algo tipo
   `https://script.google.com/macros/s/AKfycb.../exec`)
6. Guardala junto al secret en tu gestor de contraseñas

### Paso 5 · Configurar en el `.env` del dashboard

Abrí el `.env` local:

```env
APPS_SCRIPT_DRAFTS_URL=https://script.google.com/macros/s/AKfycb.../exec
APPS_SCRIPT_SHARED_SECRET=el_secret_de_32_chars_que_generaste
```

Reiniciá Flask (`Ctrl+C` y `python app.py` de nuevo).

### Paso 6 · Verificar conexión desde el dashboard

1. Abrí `http://localhost:5000`
2. Andá a **Email · Borradores Gmail** en el menú lateral
3. Click en el botón **🔌 Verificar Apps Script** arriba a la derecha
4. Deberías ver un alert:
   ```
   URL configurada: ✅
   Secret configurado: ✅
   Alcanzable: ✅
   Mensaje: OK · Apps Script accesible y secret válido
   ```

Si aparece eso, todo listo para generar borradores.

---

## Uso del módulo

### Generar tu primer batch de borradores

1. En el dashboard → **Email · Borradores Gmail**
2. Llená el formulario:
   - **Nombre del batch:** algo descriptivo (ej. *"Pizzerías Providencia Ago 2026"*)
   - **Template a usar:** elegí el rubro cuyo template querés usar
     (por ejemplo, `pizzeria`)
   - **Filtrar contactos por rubro:** típicamente el mismo rubro que
     el template
   - **Filtrar por comuna:** opcional
   - **Cantidad máxima:** 50 recomendado para arrancar (tope duro: 100)
3. Click en **👁 Preview HTML**
4. Vas a ver dos paneles:
   - **Izquierda:** primeros 25 contactos que van a recibir el borrador
   - **Derecha:** vista previa del HTML final que se va a generar para
     el primer contacto, con nombre y comercio ya reemplazados
5. Si te convence, click en **✉️ Generar borradores**
6. Confirmá el diálogo
7. En 10-30 segundos, aparece un alert:
   ```
   ✅ Batch #12 generado

   Borradores creados: 47
   Fallidos: 0
   Saltados: 3

   ¿Abrir Gmail Borradores ahora?
   ```
8. Aceptás y se abre tu Gmail en la pestaña **Borradores**
9. Revisás cada borrador · si querés editar algo puntual, lo hacés
10. Cuando estás conforme, seleccionás uno o varios y click **Enviar**

### Enviar en masa desde Gmail

Gmail no tiene un "enviar todos los borradores" nativo, pero podés:

- Abrir cada borrador y click **Enviar** (~2 segundos c/u · 50 borradores en 3 minutos)
- Con una extensión tipo *Boomerang* o *Right Inbox*, programar envíos
- Con un mini-script (opcional) que enviamos otra vez desde Apps Script

Si te interesa la opción del script para envío en lote, avisame y
extendemos `MP Prospecting Drafts` con esa capacidad.

---

## Seguridad y compliance

### Lo que ya está cubierto por diseño

| Riesgo | Mitigación |
|---|---|
| URL del Apps Script filtrada | Shared secret validado en cada request · 403 sin él |
| Payload malicioso (miles de destinos) | Tope duro 100 drafts por request en Flask + Apps Script |
| HTML injection desde `business_name` scrapeado | Jinja2 con `autoescape=True` en `draft_renderer.py` |
| Envío accidental automático | El Apps Script **solo crea drafts** · nunca envía |
| Volumen excesivo | Los drafts no cuentan contra quota de envío Gmail |
| Auditoría | Cada batch queda en `email_draft_batches` con user_id + timestamp |
| Rotación de secret | Cambiar Script Property + `.env` · reinicio de Flask |
| Compliance Ley 19.628 CL | Footer opt-out agregado automático si el template no lo trae |

### Buenas prácticas recomendadas

- **Rotá el shared secret cada 90 días** · igual que el token GitHub
- **No compartas la URL del Web App** en canales públicos · aunque
  tenga secret, exponerla innecesariamente aumenta el riesgo
- **Revisá siempre el preview HTML** antes de generar 50 borradores
- **Si te vas de MP**, borrá el Apps Script y las env vars del dashboard
  · el Web App corre bajo tus credenciales personales

### Cuando NO usar este módulo

- Para volúmenes >100 emails por batch (partí en múltiples batches o
  esperá la integración Gmail API oficial)
- Para envíos a dominios `@mercadolibre.cl` masivos internos (usá el
  Mail Service interno de Fury)
- Para mensajes transaccionales críticos (invoice, contraseñas, etc.)

---

## Troubleshooting

### "SCHEDULER DESHABILITADO" en logs de arranque

Esto es esperado si tenés `DISABLE_SCHEDULER=1` en el `.env` local.
El dashboard funciona igual, solo no dispara los cron jobs automáticos.
En producción (Fury) NO poner esa variable · los jobs deben correr.

### Apps Script devuelve 403 en el preview de health

Verificá:
1. El `SHARED_SECRET` en Script Properties del Apps Script coincide
   EXACTAMENTE con `APPS_SCRIPT_SHARED_SECRET` en el `.env` (sin
   espacios extra, sin comillas)
2. El `.env` fue leído después de reiniciar Flask (Ctrl+C y arrancar
   de nuevo)

### El preview HTML aparece vacío

Verificá:
1. Que el template del rubro tiene contenido en `et_rubro_templates.body`
2. Los filtros de contactos matchean al menos 1 lead
3. El primer contacto tiene un `business_name` no vacío

### Los drafts no aparecen en Gmail

Verificá:
1. Que autorizaste los permisos Gmail cuando corriste `testCreateDraft`
2. Los logs del Apps Script en **Executions** (menú lateral del editor)
3. Que estás mirando la cuenta correcta (a veces se mezclan
   cuentas personal y corporativa)

### Payload rechazado con "Máximo 100 drafts"

Reducí el **límite** en el dashboard a 100 y generá múltiples batches.

---

## Código completo del Apps Script

Copiá tal cual en `Code.gs` del proyecto Apps Script:

```javascript
// ═══════════════════════════════════════════════════════════════
// MP Prospecting · Generador de borradores Gmail
// Owner: Juan Sebastián Pinto (juansebastian.pinto@mercadolibre.cl)
// Uso: Web App invocado por el dashboard Flask
// ═══════════════════════════════════════════════════════════════

function getSharedSecret_() {
  const s = PropertiesService.getScriptProperties()
    .getProperty('SHARED_SECRET');
  if (!s) throw new Error('SHARED_SECRET no configurado');
  return s;
}

function doPost(e) {
  try {
    if (!e.postData || e.postData.type !== 'application/json') {
      return errorResp_(400, 'Content-Type debe ser application/json');
    }
    const body = JSON.parse(e.postData.contents || '{}');
    const provided = String(body.secret || '');
    const expected = getSharedSecret_();
    if (provided.length !== expected.length || provided !== expected) {
      console.warn('doPost: secret invalido · len=' + provided.length);
      return errorResp_(403, 'Forbidden');
    }

    const drafts = body.drafts;
    if (!Array.isArray(drafts)) {
      return errorResp_(400, 'drafts debe ser array');
    }
    if (drafts.length === 0) {
      return errorResp_(400, 'Lista de drafts vacía');
    }
    if (drafts.length > 100) {
      return errorResp_(400, 'Maximo 100 drafts por request');
    }

    const results = [];
    const errors = [];
    for (let i = 0; i < drafts.length; i++) {
      const d = drafts[i];
      try {
        if (!d.to || !d.subject || !d.htmlBody) {
          throw new Error('Faltan campos obligatorios (to, subject, htmlBody)');
        }
        const draft = GmailApp.createDraft(d.to, d.subject, '', {
          htmlBody: d.htmlBody,
          name: d.senderName || body.senderName || 'Juan Sebastián Pinto',
        });
        results.push({
          index: i,
          draftId: draft.getId(),
          to: d.to,
          ok: true,
        });
      } catch (err) {
        errors.push({
          index: i,
          to: d.to,
          error: String(err).substring(0, 200),
        });
      }
    }

    return ContentService.createTextOutput(JSON.stringify({
      ok: true,
      created: results.length,
      failed: errors.length,
      results: results,
      errors: errors,
      gmail_drafts_url: 'https://mail.google.com/mail/u/0/#drafts',
    })).setMimeType(ContentService.MimeType.JSON);

  } catch (err) {
    console.error('doPost error: ' + err);
    return errorResp_(500, 'Internal error');
  }
}

function errorResp_(status, message) {
  return ContentService.createTextOutput(JSON.stringify({
    ok: false,
    status: status,
    error: message,
  })).setMimeType(ContentService.MimeType.JSON);
}

// Función manual · para probar sin Flask
function testCreateDraft() {
  const result = GmailApp.createDraft(
    Session.getActiveUser().getEmail(),
    'Test · Draft desde Apps Script',
    '',
    {
      htmlBody: '<p>Si ves esto en tus borradores, el Apps Script anda ✅</p>',
      name: 'MP Prospecting Test',
    }
  );
  console.log('Draft ID: ' + result.getId());
}
```

---

## Referencias

- Blueprint Flask: `routes/draft_routes.py`
- Cliente HTTP: `services/apps_script_client.py`
- Renderizador templates: `services/draft_renderer.py`
- Tablas DB: `email_draft_batches`, `email_draft_batch_contacts`
- Página del dashboard: `#page-email-drafts`

---

*Última actualización: 2026-08-17 · Owner: J.S. Pinto*
