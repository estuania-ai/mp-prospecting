# MP Prospecting System · Arquitectura técnico-funcional

> Documento técnico de referencia para evaluación en Fury Project y revisiones de Seguridad Informática · MercadoPago Chile
> Owner: Juan Sebastián Pinto · Sales Executive
> Última actualización: 2026-06-09

---

## 1. Resumen ejecutivo

| Atributo | Valor |
|---|---|
| **Nombre del proyecto** | MP Prospecting System |
| **Propósito comercial** | Plataforma interna de prospección comercial · capa previa a Fast para captación y calificación de leads del segmento POS |
| **Tipo de aplicación** | Web app (Flask) con dashboard interno + scheduler de jobs |
| **Audiencia** | Equipo Sales MercadoPago Chile (Owner + TL + Sales Executives) |
| **Estado actual** | Desarrollado y operando en hosting externo (Railway) · en proceso de evaluación para migración a Fury |
| **Volumen operativo actual** | ~50 emails/día · 296 leads activos · 1.045 contactos en pool email · 12 sellers activos en fidelización |
| **Procesa PII de clientes externos** | **Sí** · ver sección "Framework regulatorio" |
| **Procesa datos financieros** | **No** · sin información de cuentas, transacciones, balances, ni movimientos MP |
| **Procesa credenciales de clientes** | **No** |

---

## 2. Diagrama de componentes (alto nivel)

```
┌─────────────────────────────────────────────────────────────────────┐
│                       USUARIOS INTERNOS MELI                         │
│  ┌──────────┐  ┌──────────┐  ┌──────────────────┐                  │
│  │  Owner   │  │   TL     │  │ Sales Executives │                  │
│  └────┬─────┘  └────┬─────┘  └────────┬─────────┘                  │
└───────┼─────────────┼─────────────────┼────────────────────────────┘
        │             │                 │
        └─────────────┴─────────────────┘
                      │ HTTPS + Flask-Login (SSO Workspace pendiente)
                      ▼
┌─────────────────────────────────────────────────────────────────────┐
│            DASHBOARD WEB · Flask 3.0.3 (Railway hoy → Fury)         │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  FRONTEND · dashboard_test14.html                            │  │
│  │  · 11 ventanas (Resumen, Leads, Interesados, Sellers,        │  │
│  │    Scraper, Inteligencia, Email, YAMM, WhatsApp, Bot, etc.)  │  │
│  │  · Server-side rendering · sin SPA frontend                  │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  BACKEND · Blueprints Flask                                  │  │
│  │  /api/leads · /api/prospects · /api/campaigns · /api/sellers │  │
│  │  /api/dashboard · /api/scraping · /api/intel · /api/manual   │  │
│  │  /api/email-tool · /api/whatsapp · /api/yamm · /auth/*       │  │
│  └──────────────────────────────────────────────────────────────┘  │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  SCHEDULER · APScheduler · 12 jobs (cron + interval)         │  │
│  │  · Scraping diario 08:00 · Email 09/12/16 · WA 09:30/15/17:30│  │
│  │  · Inbox monitor c/30min · Follow-ups c/2h · Fidelización Lu │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
        │              │                │              │
        ▼              ▼                ▼              ▼
   ┌─────────┐    ┌─────────┐     ┌──────────┐  ┌───────────┐
   │  SQLite │    │ Apify   │     │ Evolution│  │   Fast    │
   │ local   │    │ Google  │     │  API     │  │ (oficial  │
   │ DB      │    │ Maps    │     │  WhatsApp│  │  MELI)    │
   └─────────┘    └─────────┘     └──────────┘  └───────────┘

   ┌─────────────────────────────────────────────────────────┐
   │ SERVICIOS EXTERNOS (auth via API keys en .env / Vault)  │
   │ · Anthropic API (Claude Haiku · bot WA · NO operativo)  │
   │ · OpenAI API (fallback bot · NO operativo)              │
   │ · Brave Search · Google CSE · Outscraper (scraping)     │
   │ · Gmail SMTP (envío email actual · pendiente API Gmail) │
   └─────────────────────────────────────────────────────────┘
```

---

## 3. Stack tecnológico

| Capa | Tecnología | Versión | Notas |
|---|---|---|---|
| Lenguaje | Python | 3.11 | |
| Web framework | Flask | 3.0.3 | |
| Auth | Flask-Login + Werkzeug PBKDF2 | — | Cookies firmadas con `SECRET_KEY` |
| ORM / DB driver | sqlite3 (stdlib) | — | Raw SQL con params bindeados (no ORM) |
| Base de datos | SQLite | 3.x | `data/prospecting.db` · ~800 KB en local |
| Scheduler | APScheduler | 3.10 | Timezone `America/Santiago` |
| Templating | Jinja2 (Flask integrado) | — | |
| Scraping | Playwright + Requests | — | Para Fast UI y APIs externas |
| Logging | logging (stdlib) | — | File handler `logs/app.log` + stream |
| Despliegue actual | Railway | — | Hosting externo MELI (pendiente migrar) |
| Despliegue objetivo | Fury (MELI) | — | En evaluación |

---

## 4. Inventario de blueprints y endpoints principales

| Blueprint | Path base | Función |
|---|---|---|
| `auth_bp` | `/auth/*` | Login · register · cambio password · gestión usuarios |
| `leads_bp` | `/api/leads/*` | Pipeline 9 estados · filtros · import/export Excel |
| `prospects_bp` | `/api/prospects/*` | Ventana Interesados (post primer contacto) |
| `campaigns_bp` | `/api/campaigns/*` | Histórico de campañas WhatsApp |
| `sellers_bp` | `/api/sellers/*` | Sellers activos · fidelización por etapas |
| `dashboard_bp` | `/api/dashboard/*` | KPIs · embudo · charts del Resumen general |
| `scraping_bp` | `/api/scraping/*` | Scraper Google Maps vía Apify |
| `intel_bp` | `/api/intel/*` | Inteligencia · sugerencias · leads reciclables |
| `manual_bp` | `/api/manual/*` | Envío manual WhatsApp (1 a 1) |
| `fast_bp` | `/api/leads/*` | Registro automatizado en Fast (Selenium) |
| `email_bp` | `/api/email-tool/*` | Email genérico · templates · contactos |
| `whatsapp_bp` | `/api/whatsapp/*` | Status Evolution · webhook · bot config (test) |
| `yamm_bp` | `/api/yamm/*` | YAMM Mail Merge via Google Sheets (rama feature) |

### Endpoints públicos (sin login)
- `GET /health` — health check (devuelve `{ok: true}`)
- `GET /static/*` — assets estáticos
- `POST /api/whatsapp/webhook` — recibe eventos de Evolution API
- `GET /auth/login`, `POST /auth/login`

### Middleware de autenticación
- Todos los endpoints `/api/*` que no estén en la whitelist requieren login
- Cookies firmadas con `FLASK_SECRET_KEY`
- Forzar cambio de password en primer login (`password_changed = 0`)
- Cookies de sesión: configuradas para HTTPS en producción (`SESSION_COOKIE_SECURE`)
- Headers de seguridad: `X-Content-Type-Options`, `X-Frame-Options: SAMEORIGIN`, `Referrer-Policy: same-origin`

---

## 5. Modelo de datos

> Base SQLite local en `data/prospecting.db`. Schema completo en `database.py`.

### Tablas principales (24 tablas en total)

| Tabla | Filas (local) | Contenido | Sensibilidad |
|---|---:|---|---|
| `users` | n/a | Usuarios del sistema (Sales, TL, Owner) | PII interna |
| `leads` | 296 | Prospectos WhatsApp con nombre, teléfono, comuna, rubro | **PII cliente** |
| `lead_status` | 296 | Estado del pipeline por lead | — |
| `et_contacts` | 1045 | Pool email · business_name, email, phone, opt_out | **PII cliente** |
| `et_seguimientos` | 768 | Historial seguimientos email | — |
| `et_sends` | 0 | Registro envíos email (no operativo aún) | — |
| `et_campaigns` | 1 | Campañas email | — |
| `et_rubro_templates` | 18 | Templates de email por rubro | — |
| `messages` | 414 | Log mensajes WA enviados | **PII cliente** |
| `wa_messages` | 51 | Envíos WA con texto + estado | **PII cliente** |
| `wa_incoming` | 0 | Mensajes WA entrantes (bot no operativo) | **PII cliente** |
| `sellers` | 12 | Comercios activos como sellers MP | **PII cliente** |
| `opt_out` | 0 | Lista de opt-outs | **PII cliente** |
| `campaigns` | 24 | Campañas históricas | — |
| `scraping_jobs` | 5 | Jobs scraping ejecutados | — |
| `job_runs` | 40 | Histórico ejecución APScheduler | — |
| `tasks` | 6 | Tareas sobre interesados | — |
| `actividad_prospects` | 17 | Actividades registradas | — |
| `et_outscraper_queries` | 217 | Consultas Outscraper | — |
| `wa_bot_*` (5 tablas) | varias | Config + reglas + conversaciones bot (en test) | **PII cliente** |
| `yamm_campaigns` | 0 | Campañas YAMM (rama feature) | — |
| `yamm_campaign_contacts` | 0 | Contactos × campaña YAMM | **PII cliente** |
| `config` | 24 | Configuraciones del sistema | Secretos parciales |
| `importaciones` | 1 | Tracking de imports Excel | — |

### Volumen total estimado de PII almacenada
- **~1.353 personas físicas/jurídicas** identificables (296 leads + 1.045 contactos email + 12 sellers)
- Datos típicos por persona: nombre del comercio + teléfono móvil chileno + email + dirección física + comuna + rubro + histórico de mensajes
- **Sin datos financieros** (cuentas, tarjetas, balances, transacciones MP) — el sistema NO se conecta a la red transaccional de MercadoPago

---

## 6. Flujos de datos críticos

### 6.1 Flujo de captación (scraping)

```
APScheduler 08:00 ──► job_auto_scraping
                          │
                          ▼
                    Apify (Google Maps)
                          │
                          ▼
                    Validación teléfono móvil 569
                          │
                          ▼
                    INSERT INTO leads / et_contacts
                          │
                          ▼
                    Pool disponible para Sales
```

**PII generada:** sí (nombre comercio + teléfono + dirección scrapeados de fuente pública).

### 6.2 Flujo de envío email

```
APScheduler 09/12/16 ──► job_email_lote
                              │
                              ▼
                        Selección desde et_contacts (sin opt_out)
                              │
                              ▼
                        Render template Jinja2 por rubro
                              │
                              ▼
                        SMTP genérico (pendiente migrar a Gmail API / Mail Service)
                              │
                              ▼
                        INSERT INTO et_sends · tracking pixel + UUID
```

**Salida:** email a dirección externa del prospecto (Gmail, dominios varios).

### 6.3 Flujo de envío WhatsApp (Evolution)

```
APScheduler 09:30/15:00/17:30 ──► job_batch
                                       │
                                       ▼
                                Selección desde leads (estado=no_enviado)
                                       │
                                       ▼
                                Anti-spam: delay 45-240s · cap 50/día
                                       │
                                       ▼
                                HTTP POST → Evolution API (externa)
                                       │
                                       ▼
                                INSERT INTO wa_messages
```

**Servicio externo:** Evolution API (BSP no oficial · WhatsApp Web reverse-engineered).

### 6.4 Flujo de respuestas (inbox monitor)

```
APScheduler c/30min ──► job_inbox_monitor
                            │
                            ▼
                      Lectura Gmail vía Playwright headless
                            │
                            ▼
                      Match respuesta ↔ lead por dirección
                            │
                            ▼
                      UPDATE et_contacts SET email_replied=1
```

**Datos accedidos:** contenido de emails recibidos en la casilla del Owner.

### 6.5 Flujo de registro en Fast

```
Usuario marca lead como "interesado" en dashboard
        │
        ▼
   /api/leads/fast/register (manual o batch)
        │
        ▼
   Playwright headless con MP_FAST_EMAIL / MP_FAST_PASSWORD
        │
        ▼
   Login en Fast UI (no API oficial)
        │
        ▼
   Llenado de formulario · submit · validación
        │
        ▼
   UPDATE leads SET fast_ok=1
```

**⚠️ Riesgo identificado:** automatización vía credenciales corporativas MELI almacenadas en `.env`. Requiere migración a API oficial Fast o token de servicio rotable.

---

## 7. Manejo de secretos

### Secretos en uso actualmente (21 variables)

| Secreto | Tipo | Almacenamiento actual | Riesgo |
|---|---|---|---|
| `FLASK_SECRET_KEY` | Internal | `.env` + Railway env vars | Bajo |
| `ANTHROPIC_API_KEY` | API key terceros | `.env` + Railway | Medio · billing personal |
| `OPENAI_API_KEY` | API key terceros | `.env` + Railway | Medio · billing personal |
| `EVOLUTION_API_KEY` / `_URL` / `_INSTANCE` | BSP externo | `.env` + Railway | Medio |
| `BRAVE_SEARCH_API_KEY` | API key terceros | `.env` + Railway | Bajo |
| `GOOGLE_CSE_API_KEY` / `_CX` | API key Google | `.env` + Railway | Bajo |
| `OUTSCRAPER_API_KEY` | API key terceros | `.env` + Railway | Bajo |
| **`MP_FAST_EMAIL` / `MP_FAST_PASSWORD`** | **Corporativo MELI** | `.env` + Railway | **🔴 Alto** |
| `APP_BASE_URL` | Configuración | `.env` + Railway | Ninguno |
| `EMAIL_FROM` / `EMAIL_FROM_NAME` / `EMAIL_FROM_PHONE` | Configuración | `.env` + Railway | Ninguno |
| `EMAIL_LOCAL_TOKEN` / `_URL` | Servicio interno | `.env` + Railway | Bajo |
| `FAST_LOCAL_TOKEN` / `_URL` / `_SESSION_JSON` | Sesión Fast | `.env` + Railway | Medio |
| `FAST_HEADLESS` | Configuración | `.env` + Railway | Ninguno |
| `BOOKING_URL` | Configuración (Calendly) | `.env` + Railway | Ninguno |
| `BRAVE_MONTHLY_LIMIT` | Rate limit | `.env` + Railway | Ninguno |
| `ANTHROPIC_BOT_MODEL` / `OPENAI_BOT_MODEL` | Configuración | `.env` + Railway | Ninguno |

### Mecanismos de protección actuales
- `.env` en `.gitignore` (auditado)
- Token GitHub rotado a Fine-grained con scope mínimo (Contents R/W + Metadata RO solo en este repo) · expira en 90 días · guardado en Windows Credential Manager
- Variables en Railway: cifradas en reposo según política Railway · accesibles solo a admins del proyecto Railway

### Mecanismos pendientes de implementar
- Migrar todos los secretos a **Fury Secrets / Vault** post-migración
- Reemplazar `MP_FAST_PASSWORD` por token de sesión OAuth o acceso vía API oficial Fast (pendiente disponibilidad)
- Rotación automática programada (90 días)

---

## 8. Integraciones externas

| Servicio | Propósito | Tipo | Aprobado MELI |
|---|---|---|---|
| **Apify** | Scraping Google Maps | API REST | ⏳ Pendiente declarar |
| **Outscraper** | Scraping alternativo | API REST | ⏳ Pendiente declarar |
| **Brave Search** | Búsqueda complementaria | API REST | ⏳ Pendiente declarar |
| **Google Custom Search** | Búsqueda complementaria | API REST | ⏳ Pendiente declarar |
| **Anthropic Claude** | Bot RAG (en test, no operativo) | API REST | ⏳ LLM Studio aprobado en Fury |
| **OpenAI** | Fallback bot (no operativo) | API REST | ⏳ Pendiente |
| **Evolution API** | WhatsApp gateway no-oficial | API REST + Webhook | ⛔ NO aprobado oficial |
| **Gmail SMTP** | Envío email | SMTP | ⏳ Pendiente reemplazar por Mail Service interno |
| **Gmail inbox** | Lectura respuestas | Playwright (UI scraping) | ⛔ Frágil · pendiente migrar a Gmail API |
| **Fast** | Registro de leads | Playwright (UI automation) | ⛔ Sin API oficial documentada |
| **Calendly** | Agendamiento reuniones | URL pública | ✅ Sin API · solo redirect |
| **YAMM** | Mail Merge via Google Sheets | Indirecto (via Sheet) | ✅ Workspace MELI |

---

## 9. Observabilidad y trazabilidad

| Aspecto | Implementación actual | Gap vs estándar Fury |
|---|---|---|
| **Logs aplicación** | `logging` stdlib · file `logs/app.log` + stdout | Falta integración Kibana |
| **Métricas** | KPIs en dashboard (queries directas a DB) | Falta integración Datadog |
| **Trazas** | No implementado | New Relic disponible en Fury |
| **Audit log** | `logger.info()` con user_id en endpoints críticos | Falta tabla `audit_events` formal |
| **Alertas** | No implementado | Pendiente definir SLIs |
| **Health checks** | `GET /health` (200 fijo) | Pendiente extender a DB + integraciones |
| **Backups DB** | Manual desde Railway | Falta backup automatizado a Object Storage |

---

## 10. Framework regulatorio aplicable

> **Esta sección responde explícitamente a la pregunta de Fury Project: "¿El proyecto está bajo algún framework regulatorio?"**

### 10.1 Respuesta corta

**Sí.** El proyecto procesa datos personales (PII) de personas físicas y jurídicas chilenas en el contexto de actividad comercial. Por lo tanto aplican múltiples marcos regulatorios chilenos, internos MELI y de plataformas terceras. **Actualmente el proyecto NO tiene una declaración formal de compliance**, lo cual es justamente uno de los motivos para migrarlo a Fury.

### 10.2 Marcos regulatorios aplicables

#### a) Legislación chilena de protección de datos

| Norma | Aplicación |
|---|---|
| **Ley 19.628** (Protección de la Vida Privada · 1999) | Aplica · regula tratamiento de datos personales · derechos del titular (ARCO) |
| **Ley 21.719** (Nueva Ley de Protección de Datos Personales · 2024) | Aplica · crea la **Agencia de Protección de Datos** · vigencia diferida pero el proyecto debe estar listo · obliga a base legal explícita, DPO, registro de tratamientos, evaluación de impacto (EIPD) para tratamientos de alto riesgo |
| **Ley 19.496** (Derechos del Consumidor) | Aplica · comunicaciones comerciales requieren consentimiento e información clara |
| **Ley 19.628 art. 4 letra g (interés legítimo)** | Posible base legal para prospección B2B · sujeta a balanceo de derechos |

#### b) Legislación financiera (NO aplica directamente)

| Norma | Aplica al proyecto? |
|---|---|
| **Ley 21.521** (Fintech) y normativa CMF | **No directamente** · el proyecto no procesa transacciones, dinero, ni datos de cuentas MP · es solo prospección comercial |
| **NCG 461 CMF** (Norma sobre ciberseguridad) | Aplica a MercadoPago como entidad fiscalizada · el proyecto debe alinearse a las políticas corporativas que derivan de esta norma |
| **Política interna MELI de PII** | Aplica · clasificación y manejo de datos sensibles |

#### c) Plataformas terceras

| Política | Aplicación |
|---|---|
| **Meta WhatsApp Business Policy** | Aplica si se envía con WA Business API · prohíbe spam, requiere opt-in en algunos casos, exige opt-out funcional |
| **WhatsApp Commerce Policy** | Aplica · restricciones sobre contenido comercial |
| **Google Maps Platform Terms** | Aplica al uso de datos scrapeados de Google Maps |
| **Apify Terms of Service** | Aplica al uso del servicio de scraping |
| **Anthropic Acceptable Use** | Aplicaría si el bot RAG entrara en producción |

#### d) Internas MELI

| Política | Aplicación |
|---|---|
| **Política de Seguridad Informática** | Aplica · acceso a infraestructura, manejo de secretos, gestión de incidentes |
| **Política de Datos Personales MELI** | Aplica · clasificación tier 1-2 (PII no financiera de prospectos) |
| **Código de Ética y Compliance** | Aplica · uso adecuado de recursos corporativos, marca, etc. |
| **Política de uso de marca** | Aplica · cualquier comunicación con identidad MP requiere autorización formal |

### 10.3 Datos personales tratados y bases legales

| Categoría de dato | Cantidad estimada | Origen | Base legal propuesta |
|---|---|---|---|
| Nombre comercial (negocio) | ~1.353 | Scraping fuente pública (Google Maps) | Interés legítimo (Art. 4 Ley 19.628) |
| Teléfono móvil chileno | ~1.353 | Scraping fuente pública | Interés legítimo + consentimiento al responder |
| Email comercial | ~1.045 | Scraping fuente pública | Interés legítimo |
| Dirección física | ~1.353 | Scraping fuente pública | Interés legítimo |
| Rubro y categoría comercial | ~1.353 | Clasificación interna | Interés legítimo |
| Contenido de mensajes intercambiados | ~465 (414 + 51) | Generado en la interacción | Consentimiento al iniciar conversación |
| Estado del pipeline / opt-outs | ~1.353 | Generado por el sistema | Cumplimiento de obligaciones (opt-out) |

**Nota:** El uso de "interés legítimo" como base legal para prospección B2B es legítimo bajo Ley 21.719, pero requiere documentar el balanceo de derechos del titular, **lo cual hoy no está formalizado**.

### 10.4 Derechos del titular (Ley 19.628 / 21.719)

| Derecho | Implementación actual | Gap |
|---|---|---|
| **Acceso** (saber qué datos se tienen) | No automatizado · respondible manualmente | Falta endpoint de exportación por titular |
| **Rectificación** | Editable desde dashboard por Sales | Sin canal para que el titular solicite |
| **Cancelación / Supresión** | Manual desde dashboard | Falta canal externo (ej. responder "BAJA" funciona solo para WhatsApp) |
| **Oposición** | Opt-out registrado en `et_contacts.opt_out` | Funciona para email/WA · falta documento de aviso |
| **Portabilidad** (Ley 21.719) | No implementado | Pendiente |

### 10.5 Retención de datos

| Tipo de dato | Retención actual | Retención recomendada |
|---|---|---|
| Leads pendientes | Indefinida | Máximo 24 meses desde scraping si no hubo interacción |
| Conversaciones WA/Email | Indefinida | 12 meses para fines comerciales · 5 años si hubo conversión |
| Opt-outs | Indefinida | Permanente (para garantizar el derecho) |
| Logs aplicación | Sin política | 90 días en línea + archivo cifrado |

### 10.6 Procesadores de datos terceros (DPA status)

| Procesador | Trata PII? | DPA firmado con MELI? |
|---|---|---|
| Railway (hosting) | Sí (toda la BD) | ❓ Pendiente verificar |
| Apify | No (genera datos públicos, no procesa privados) | N/A |
| Evolution API | Sí (mensajes WhatsApp) | ❌ No (servicio no oficial) |
| Gmail / Google Workspace | Sí (emails) | ✅ Cubierto por contrato Workspace MELI |
| Outscraper / Brave / Google CSE | No (queries de búsqueda sin PII saliente) | N/A |
| Anthropic / OpenAI | Sí si el bot opera (mensajes de clientes) | ❌ No (servicio externo no aprobado para producción) |

### 10.7 Notificación de brechas

**Estado actual:** sin proceso formal.

**Requerido por Ley 21.719:** notificación a la Agencia de Protección de Datos dentro de 72h ante brecha que afecte derechos de titulares. MELI tiene proceso interno (a través del equipo de Seguridad Informática) que el proyecto debe seguir.

### 10.8 Resumen de gaps de compliance y acciones recomendadas

| # | Gap | Severidad | Acción propuesta |
|---|---|---|---|
| 1 | Sin declaración formal de tratamiento bajo Ley 19.628 | 🔴 Alta | Declarar el sistema al DPO MELI |
| 2 | Sin DPA firmado con Railway (procesador externo) | 🔴 Alta | Migrar a Fury (resuelve) |
| 3 | Evolution API sin DPA y no aprobado | 🔴 Alta | Migrar a BSP oficial (Vambe, Twilio con contrato, etc.) |
| 4 | `MP_FAST_PASSWORD` en `.env` (credencial corporativa) | 🔴 Alta | Migrar a token de sesión rotable o API oficial Fast |
| 5 | Sin canal automático para ejercicio de derechos ARCO | 🟡 Media | Implementar endpoint `/privacy/request` |
| 6 | Webhook de Evolution sin validación HMAC | 🟡 Media | Implementar firma compartida (CWE-345) |
| 7 | Sin política de retención implementada | 🟡 Media | Definir y agendar job de purge automático |
| 8 | Bot RAG con Anthropic API personal (no operativo) | 🟢 Baja | Migrar a LLM Studio en Fury cuando se reactive |
| 9 | Sin backup automatizado de la BD | 🟡 Media | Resuelto en Fury (MySQL gestionado con backups) |
| 10 | Sin EIPD (evaluación de impacto en privacidad) | 🟡 Media | Realizar EIPD según Ley 21.719 si se considera "alto riesgo" |

---

## 11. Categorización propuesta del proyecto en Fury

| Atributo | Valor propuesto | Justificación |
|---|---|---|
| **Data Tier** | Tier 2 (Confidencial · PII no financiera) | Maneja datos personales pero no transaccionales |
| **Criticidad operacional** | Tier 3 (No crítico) | Una caída de horas no afecta operación core de MP |
| **Categoría de aplicación** | Internal Business Tool · Sales Productivity | Solo usuarios internos · sin clientes externos como usuarios |
| **Audiencia** | Internal MELI staff únicamente | Sales + TL + Owner |
| **Exposición de red** | Internal-only post-migración | Hoy público en Railway · objetivo: interno MELI |
| **Necesidades de cumplimiento** | Ley 19.628/21.719 CL · Política PII MELI · Políticas Meta para WA | Sin obligaciones CMF directas |

---

## 12. Roadmap propuesto para alineación con Fury

### Fase 1 · Pre-migración (semanas 1-2)
- Declaración formal del proyecto al DPO MELI
- Aprobación de uso de marca MP por Marketing/Legal
- Identificación de sponsor de Engineering
- Decisión sobre el incidente de Seguridad abierto (proyecto Railway)

### Fase 2 · Migración técnica (semanas 3-5)
- Setup en Fury con sponsor Engineering
- Migración SQLite → MySQL gestionado
- Migración secretos `.env` → Fury Secrets
- Migración jobs APScheduler → Verdi Flows
- Reemplazo Evolution API por BSP oficial
- Implementación de validación HMAC y rate limiting

### Fase 3 · Compliance (semanas 6-7)
- Implementación de endpoints de derechos ARCO
- Política de retención automatizada
- Audit log formal en tabla dedicada
- EIPD documentada
- Backup automatizado a Object Storage

### Fase 4 · Decomisionar Railway (semana 8)
- Validación de paridad funcional
- Cutover ordenado
- Borrado seguro de datos en Railway tras período de gracia
- Cierre formal del incidente con Seguridad

---

## 13. Referencias

- Ley 19.628 · Sobre Protección de la Vida Privada (Chile, 1999)
- Ley 21.719 · Nueva Ley de Protección de Datos Personales (Chile, 2024)
- Ley 19.496 · Sobre Protección de los Derechos de los Consumidores (Chile, 1997)
- NCG 461 CMF · Norma sobre Gestión de la Ciberseguridad
- WhatsApp Business Solution Terms · Meta Platforms Inc.
- Política interna MELI de Seguridad Informática (referencia interna)
- Política interna MELI de Protección de Datos Personales (referencia interna)
- Documento STATUS.md del proyecto · auditoría interna 2026-05-15

---

*Fin del documento. Versión 1.0 · 2026-06-09 · J.S. Pinto*
