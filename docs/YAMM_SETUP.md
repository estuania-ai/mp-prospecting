# YAMM Integration — Mail Merge vía Google Sheets

> Guía operativa para enviar campañas email masivas usando YAMM desde
> el dashboard MP Prospecting, sin necesidad de API Gmail completa.

---

## ¿Qué es esto?

**YAMM** (Yet Another Mail Merge) es un complemento de Google Workspace
que envía emails personalizados desde tu Gmail leyendo destinatarios
desde un Google Sheet.

Con esta integración:
- Filtrás leads desde el dashboard
- Generás un CSV listo para YAMM
- Lo pegás en un Google Sheet
- Corrés YAMM (1 click)
- YAMM envía los emails personalizados desde tu cuenta `@mercadolibre.cl`
- Cuando termina, exportás el Sheet a CSV con los resultados
- Subís ese CSV al dashboard → se actualizan las métricas

**Lo que NO requiere:**
- API Gmail (sigue pendiente de autorización · no la necesitamos)
- API Sheets (versión futura · por ahora flujo CSV manual)
- Pago adicional · YAMM va con tu plan Workspace corporativo

**Lo que SÍ requiere:**
- YAMM instalado en tu cuenta `@mercadolibre.cl` (ya lo tenés)
- Cualquier navegador moderno
- 3 clicks manuales tuyos por campaña

---

## Pre-requisitos

- [x] Cuenta corporativa Google Workspace con YAMM habilitado
- [ ] Tener al menos 1 template Gmail guardado como **Borrador** (drafts) que
      use variables como `{{Nombre}}`, `{{Comercio}}`, `{{Rubro}}`
- [ ] Footer opt-out incluido en el template (legal Chile, Ley 19.628)

### Cómo crear el template Gmail

1. Abrí Gmail → **Redactar**
2. En el cuerpo escribís el email con variables entre llaves dobles, ej:

```
Hola {{Nombre}} 👋

Vi {{Comercio}} en {{Comuna}} y me parece que MercadoPago Point puede
serles muy útil para cobrar con tarjeta sin arriendo mensual.

Las pizzerías como la tuya están aprovechando muy bien las cuotas sin
interés Visa/Master y la liquidez inmediata (incluso findes).

¿Querés que te llame esta semana para mostrarte cómo funciona?

Saludos,
Juan Sebastián
Sales Executive · MercadoPago Chile

---
Si no querés recibir más mensajes, respondé "BAJA" y no te
contactaremos más.
```

3. Asunto: similar (usa variables si querés personalizar)
4. **Cerrás la ventana** sin enviar — Gmail lo guarda como borrador
5. Ese borrador es el que vas a elegir cuando corras YAMM

> Tip: creá un borrador por rubro · YAMM lee el "Subject" del borrador
> para identificarlo en la lista.

---

## Flujo completo paso a paso

### Paso 1 — Filtrar leads y generar CSV (en el dashboard)

1. Andá a **Email · YAMM** en el menú lateral
2. Llená el formulario:
   - **Nombre de la campaña**: descriptivo (ej. *"Pizzerías Las Condes - Mayo 2026"*)
   - **Asunto del email**: para referencia (no se envía, es solo nota)
   - **Rubro / Comuna / Estado**: filtros
   - **Máximo destinatarios**: 200 por defecto · tope 2000
3. Click en **👁 Preview** → ves cuántos leads matchean
4. Click en **⬇ Generar CSV YAMM** → descarga el archivo `yamm_campaign_<id>_<timestamp>.csv`

### Paso 2 — Crear el Google Sheet y pegar el CSV

1. Andá a [sheets.google.com](https://sheets.google.com) → **Nuevo Sheet** en blanco
2. Nombralo con el mismo nombre de la campaña (para no perderte)
3. Click en la celda **A1**
4. **Archivo → Importar → Subir → arrastrá el CSV** descargado
5. En el diálogo:
   - "Reemplazar hoja actual"
   - Tipo separador: "Detectar automáticamente" (o "Coma")
   - Convertir texto en números/fechas: **Sí**
6. **Importar datos**

Vas a ver las columnas:

| Email | Nombre | Comercio | Rubro | Comuna | Telefono | ContactId | CampaignId | Merge status | Date sent | Date opened | Date clicked | Date responded | Comments |

Las 6 columnas finales (Merge status hacia adelante) están vacías — YAMM las va a rellenar.

### Paso 3 — Correr YAMM

1. En el Sheet, **Extensiones → Yet Another Mail Merge → Start mail merge**
2. YAMM detecta automáticamente la columna `Email`
3. Te pregunta qué template Gmail usar → seleccioná el borrador que creaste
4. **Send N emails** → confirma

YAMM empieza a enviar a un ritmo que respeta los límites de Gmail
(~1000 emails/día con Workspace Business · más que suficiente para vos).

A medida que envía, va rellenando las columnas en el Sheet en tiempo real:
- `Merge status`: `SENT`, `OPENED`, `CLICKED`, `RESPONDED`, `BOUNCED`, `ERROR`
- `Date sent`: timestamp de cuando salió
- `Date opened`: timestamp de primera apertura del cliente
- `Date clicked`: si tenías link, primer click
- `Date responded`: si te respondieron
- `Comments`: notas adicionales (ej. razón de bounce)

### Paso 4 — Exportar el Sheet a CSV con los resultados

Una vez que YAMM terminó (o cuando quieras hacer un corte intermedio):

1. En el Sheet → **Archivo → Descargar → Valores separados por comas (.csv)**
2. Guardá el archivo

### Paso 5 — Subir resultados al dashboard

1. Volvé a **Email · YAMM** en el dashboard
2. En la tabla "Historial de campañas YAMM", buscá la fila de tu campaña
3. En la columna **Subir resultados**, click en el input de archivo y elegí el CSV
4. Confirmá el upload
5. Aparece un alert con el resumen:
   - Cuántos contactos se actualizaron
   - Cuántas aperturas
   - Cuántas respuestas
   - Cuántos rebotes

A partir de ese momento:
- La campaña queda como **"enviada"** en el historial
- Los leads tienen marcadas las aperturas/respuestas/rebotes
- Los rebotes se marcan en `et_contacts.email_bounced = 1` para
  excluirlos de futuras campañas

---

## Notas de seguridad y compliance

### PII en CSVs descargados
- El CSV que descargás contiene emails, nombres y teléfonos de leads
- **Borralo de tu PC** después de subirlo al Google Sheet
- No lo dejes en Downloads ni lo subas a ningún Drive personal

### Footer opt-out obligatorio
- Ley 19.628 (Chile) y buenas prácticas exigen que todo email comercial
  tenga forma clara de darse de baja
- El template Gmail debe incluir: *"Si no querés recibir más mensajes,
  respondé BAJA"* o equivalente
- Si un cliente responde "BAJA" / "STOP" / "opt-out", marcalo en el
  dashboard como `opt_out=1` para excluirlo de futuras campañas

### Auditoría de envíos
- Cada export al CSV queda registrado en logs (`logger.info` con quien
  exportó, cuántos contactos, cuándo)
- Cada import también queda logueado
- Los rebotes se persisten para que el dashboard te evite re-enviarles

### Límites de envío de Gmail Workspace
- Plan Business Starter: ~500 emails/día por usuario
- Plan Business Standard/Plus: ~2000 emails/día
- Para 50 envíos/día estás holgadísimo

---

## Solución de problemas

**El CSV descargado abre raro en Excel (acentos cuadrados):**
- El CSV tiene BOM UTF-8 · debería abrir bien con doble-click
- Si Excel sigue dando problemas, abrilo desde Google Sheets directo
  (mejor que Excel para este flujo)

**YAMM dice "no Email column found":**
- Asegurate de que la columna se llama exactamente `Email` (con mayúscula)
- Si pegaste el CSV mal y quedaron datos corridos, importá de nuevo

**Pegué el CSV y aparece todo en una sola columna:**
- En el diálogo de importación elegí separador "Coma" explícitamente
- O usá Datos → Dividir texto en columnas

**Subí el CSV de resultados pero dice "0 actualizados":**
- Verificá que la columna `ContactId` esté presente y con valores
- Si la borraste o YAMM la sobrescribió, podés mapear por Email (futura mejora)

**Los emails están saliendo desde la cuenta equivocada:**
- En YAMM → Settings → Sender → verificá que esté tu cuenta `@mercadolibre.cl`
- Si tenés alias configurados, podés elegir cuál usar

---

## Futuro · Fase 2 (cuando llegue API Sheets)

Lo que se va a automatizar:
- El dashboard crea el Sheet directamente (sin descargar CSV)
- Te lo comparte por mail
- Lee los resultados sin que tengas que exportar CSV
- Triggers automáticos: si un lead responde "interesado", se mueve
  directo a la ventana de Interesados del dashboard

Mientras tanto, el flujo manual de arriba te deja operativo desde el
día 1, sin esperar autorizaciones.

---

*Última actualización: 2026-05-16 · Owner: J.S. Pinto*
