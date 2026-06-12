# MP Prospecting System · Brief ejecutivo para Fury Project

> Documento de 1 página para evaluación de migración a Fury · responde a las preguntas estándar del cuestionario de aprobación.
> Owner: Juan Sebastián Pinto · Sales Executive · MercadoPago Chile · 2026-06-12
> Referencia detallada: `docs/ARCHITECTURE.md` (mismo repo)

---

## 1. Identificación

**Nombre:** MP Prospecting System
**Propósito:** Plataforma interna de prospección comercial para el equipo Sales POS de MercadoPago Chile. Actúa como **capa previa a Fast** · captura leads desde fuentes públicas, los califica vía contacto comercial, y los entrega al flujo oficial de Fast cuando muestran interés. **No reemplaza a Fast**.
**Tipo:** Web app Flask 3 + SQLite + APScheduler (12 jobs · L-V).
**Audiencia:** Sólo usuarios internos MELI (Owner + TL + Sales Executives).
**Stack:** Python 3.11 · Flask · SQLite · Playwright · APScheduler · 21 env vars · Hosting actual: Railway.

---

## 2. Categorización Fury propuesta

| Atributo | Valor | Justificación |
|---|---|---|
| **Data Tier** | **Tier 2** (Confidencial · PII no financiera) | Procesa nombres, teléfonos, emails y direcciones de prospectos comerciales. No procesa datos transaccionales ni financieros MP. |
| **Criticidad operacional** | **Tier 3** (No crítico) | Una caída no afecta la operación core de MP · es una herramienta de productividad. |
| **Exposición de red** | **Internal-only post-migración** | Hoy en Railway (externa) · objetivo: red interna MELI. |
| **Audiencia** | **Internal staff únicamente** | Sin clientes externos como usuarios. |
| **Volumen actual** | ~50 emails/día · 296 leads · 1.045 contactos email · 12 sellers | Volumen bajo · compatible con cuotas estándar. |
| **Datos financieros / transaccionales** | **No** | Sin acceso a red transaccional MP. |

---

## 3. Framework regulatorio aplicable

| Marco | Aplica | Estado |
|---|---|---|
| **Ley 19.628 CL** · Protección de la Vida Privada | ✅ Sí | Pendiente declaración formal al DPO MELI |
| **Ley 21.719 CL** · Nueva Ley de Protección de Datos Personales (2024) | ✅ Sí | Pendiente · debe estar listo para vigencia plena |
| **Ley 19.496 CL** · Derechos del Consumidor | ✅ Sí | Cumple con opt-out funcional en email/WA |
| **NCG 461 CMF** · Ciberseguridad | ✅ Indirecta | Vía políticas corporativas MELI |
| **Regulación CMF / Ley Fintech 21.521** | ❌ No directamente | Sin procesamiento transaccional |
| **WhatsApp Business / Commerce Policy** (Meta) | ✅ Sí | Aplica si se activa BSP oficial |
| **Política PII MELI** · interna | ✅ Sí | Pendiente declaración formal |
| **Política de Seguridad Informática MELI** · interna | ✅ Sí | Incidente abierto en revisión |
| **Política de uso de marca MELI** · interna | ✅ Sí | Pendiente autorización formal para uso identidad MP en mensajes |

---

## 4. Procesadores terceros con PII · DPA status

| Procesador | Trata PII? | DPA con MELI |
|---|---|---|
| Railway (hosting actual) | Sí · toda la BD | ❓ Por verificar |
| Gmail / Google Workspace | Sí · emails | ✅ Cubierto por contrato Workspace MELI |
| Evolution API (WhatsApp gateway no oficial) | Sí · mensajes WA | ❌ **No · pendiente migrar a BSP oficial** |
| Anthropic / OpenAI (bot RAG no operativo) | Sí si opera | ❌ Pendiente · LLM Studio Fury sería el reemplazo |
| Apify · Outscraper · Brave · Google CSE | No (queries sin PII saliente) | N/A |
| Calendly | No (redirect a URL pública) | N/A |
| YAMM (vía Google Workspace) | Indirecto | ✅ Cubierto por contrato Workspace |

---

## 5. Gaps de compliance · top 5 priorizados

| # | Gap | Severidad | Resolución |
|---|---|---|---|
| 1 | Hosting externo (Railway) sin DPA verificado | 🔴 Alta | **Migración a Fury** (este pedido) |
| 2 | Evolution API · sin DPA · servicio no oficial | 🔴 Alta | Reemplazar por BSP oficial (Twilio oficial vía IAM Media, o agencia con contrato) |
| 3 | `MP_FAST_PASSWORD` en `.env` (credencial corporativa MELI) | 🔴 Alta | Migrar a token de sesión rotable o API oficial Fast |
| 4 | Sin declaración formal al DPO MELI | 🟡 Media | Iniciar trámite paralelo a la migración |
| 5 | Webhook Evolution sin validación HMAC (CWE-345) | 🟡 Media | Implementar firma compartida pre-migración |

Gaps adicionales documentados en `docs/ARCHITECTURE.md` sección 10.8.

---

## 6. Plan de migración propuesto · 4 fases · ~8 semanas

| Fase | Duración | Actividades clave |
|---|---|---|
| **1 · Pre-migración** | 1-2 sem | Declaración al DPO · autorización uso de marca · identificación sponsor Engineering · resolución incidente Seguridad abierto |
| **2 · Migración técnica** | 2-3 sem | Setup Fury · SQLite → MySQL gestionado · `.env` → Fury Secrets · APScheduler → Verdi Flows · BSP oficial · validación HMAC + rate limiting |
| **3 · Compliance** | 1-2 sem | Endpoints ARCO · política retención automatizada · audit log formal · EIPD · backup automatizado a Object Storage |
| **4 · Cutover** | 1 sem | Paridad funcional validada · cutover ordenado · borrado seguro Railway · cierre incidente Seguridad |

---

## 7. Pendientes / dependencias externas

- **Sponsor de Engineering** para crear namespace en Fury (no identificado aún)
- **Resolución del incidente abierto con Seguridad Informática** sobre tráfico hacia Railway
- **Autorización formal de marca MP** para mensajería con identidad corporativa
- **Coordinación con IAM Media** para vinculación oficial del número WhatsApp al portfolio Meta de MP (proceso independiente paralelo)
- **Acceso a API Google Sheets** (en gestión) para automatizar el flujo YAMM

---

## 8. Información de contacto

| Rol | Persona | Contacto |
|---|---|---|
| Owner del proyecto | Juan Sebastián Pinto · Sales Executive | juansebastian.pinto@mercadolibre.cl |
| Sponsor Engineering | **Pendiente de asignación** | — |
| DPO responsable | **Pendiente de declarar** | — |
| Equipo IAM Media (canal WA oficial) | — | iam_soporte_rrss@mercadolibre.com |

---

*Versión 1.0 · 2026-06-12 · Documento de 1 página para Fury Project · Detalle completo en `docs/ARCHITECTURE.md`*
