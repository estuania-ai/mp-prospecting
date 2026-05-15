# STATUS — MP Prospecting System
> Documento técnico-funcional del estado real del proyecto · actualizado 2026-05-15
> Owner: Juan Sebastián Pinto · Sales Executive · MercadoPago Chile

---

## Resumen ejecutivo

| Componente | Estado | Acción requerida |
|---|---|---|
| Dashboard web (Railway) | 🟢 Operativo | Mantenimiento de funcionalidad |
| Base de datos SQLite | 🟡 Funcional sin backup automático | Implementar backup periódico |
| Jobs APScheduler (12) | 🟢 Definidos · pendiente validar ejecución real | Auditoría de últimas corridas |
| Scraping Google Maps (Apify) | 🟢 Operativo | OK |
| Prospección Email | 🔴 `et_sends = 0` · nunca se envió | Decidir: completar o desactivar UI |
| Prospección WhatsApp (Evolution) | 🟡 51 mensajes históricos · webhook intermitente | Monitor en producción |
| Bot WhatsApp conversacional | 🔴 No operativo (en test) | Mantener en rama experimental |
| Inbox monitor Gmail | 🟢 Operativo cada 30 min | OK |
| Fidelización sellers (12 sellers) | 🟢 Operativo · 5 etapas | OK |
| Respaldo en GitHub | 🟢 Sincronizado · token rotado | OK (validado 2026-05-15) |

---

## 1. Seguridad y respaldo

### 1.1 Estado actual del repositorio
- ✅ `estuania-ai/mp-prospecting` con todos los commits hasta `30c16a9` pusheados
- ✅ Token GitHub rotado a fine-grained con scope `Contents: Read/Write` + `Metadata: Read` solo sobre `mp-prospecting`
- ✅ Token guardado en Windows Credential Manager (cifrado) — fuera de `.git/config`
- ✅ Expiración 90 días (próxima rotación: **2026-08-13**)
- ✅ `.gitignore` cubre `.env`, `*.db`, `auth_info/`, scripts de debug y assets temporales

### 1.2 Secretos / credenciales en uso (de `.env`)
> **TODOS los siguientes deben estar SOLO en Railway env vars y `.env` local · jamás en código:**

- `FLASK_SECRET_KEY` — sesiones Flask
- `ANTHROPIC_API_KEY` — bot WA (en test) · billing personal
- `OPENAI_API_KEY` — fallback bot
- `EVOLUTION_API_KEY` / `EVOLUTION_API_URL` / `EVOLUTION_INSTANCE` — WhatsApp gateway
- `BRAVE_SEARCH_API_KEY` / `GOOGLE_CSE_API_KEY` — búsquedas
- `OUTSCRAPER_API_KEY` — scraping alternativo
- `MP_FAST_EMAIL` / `MP_FAST_PASSWORD` — **CREDENCIALES CORPORATIVAS MELI** ⚠️
- `APP_BASE_URL` — URL pública Railway

### 1.3 Riesgos identificados (pendientes de mitigar)

| Riesgo | Severidad | Mitigación propuesta |
|---|---|---|
| `MP_FAST_PASSWORD` (clave corporativa MELI) almacenada en plano en Railway | 🔴 Alta | Mover a token de sesión rotable · evaluar si el flujo Fast puede usar API en vez de scraping de UI con usuario/pass |
| Webhook `/api/whatsapp/webhook` no valida firma del emisor | 🟡 Media | Agregar HMAC compartido con Evolution (CWE-345) |
| Backup BD producción depende de Railway sin replicación externa | 🟡 Media | Dump diario a Object Storage / repo privado cifrado |
| `app_pythonanywhere.py` legacy en raíz del repo | 🟢 Baja | Mover a `legacy/` o borrar |
| Scripts `check_*.py` / `fix_*.py` sueltos en raíz | 🟢 Baja | Limpiar (ya están en gitignore pero contaminan el directorio) |

---

## 2. Estado de la base de datos (snapshot local 2026-05-06)

> Conteos de la BD local de desarrollo. La BD productiva en Railway puede diferir.

| Tabla | Filas | Comentario |
|---|---:|---|
| `leads` | 296 | Leads activos en pipeline |
| `lead_status` | 296 | Coincide con leads · integridad OK |
| `et_contacts` | 1045 | Pool email prospección |
| `et_seguimientos` | 768 | Historial seguimientos email |
| `et_sends` | **0** | 🔴 Nunca se ejecutó envío email desde BD local |
| `et_reuniones` | 0 | |
| `et_rubro_templates` | 18 | Templates email por rubro |
| `et_outscraper_queries` | 217 | Histórico búsquedas Outscraper |
| `wa_incoming` | **0** | 🔴 Nunca recibió webhook WA entrante |
| `wa_messages` | 51 | Salidas WA registradas |
| `messages` | 414 | Log general mensajes |
| `prospects` | 13 | |
| `sellers` | 12 | En fidelización · día 0-40 |
| `opt_out` | 0 | (en producción Railway hay 3) |
| `campaigns` | 24 | |
| `et_campaigns` | 1 | |
| `scraping_jobs` | 5 | |
| `job_runs` | 40 | Histórico ejecución APScheduler |
| `tasks` | 6 | Tareas asignadas a interesados |
| `actividad_prospects` | 17 | Actividad sobre interesados |
| `importaciones` | 1 | |

### Hallazgos clave
1. **`et_sends = 0` confirma que la ventana "Email · Leads" estaba vacía**: el flujo de envío email nunca se completó en BD local. En Railway pueden existir registros, hay que verificar.
2. **`wa_incoming = 0`**: el bot WA nunca recibió un webhook real procesado correctamente · consistente con la realidad de que está en test.
3. **Integridad `leads` ↔ `lead_status`**: 296 = 296. OK.

---

## 3. Jobs APScheduler (12 trabajos programados)

> Zona horaria: `America/Santiago` · configurados en `app.py`

| # | Job | Trigger | Función |
|---|---|---|---|
| 1 | `job_auto_scraping` | Diario 08:00 | Scraping automático Google Maps |
| 2 | `job_email_lote1` | Lun-Vie 09:00 | Primera tanda email del día |
| 3 | `job_batch1` (WA) | Lun-Vie 09:30 | Primera tanda WhatsApp |
| 4 | `job_wa_followup` | Diario 10:00 | Re-contacto WA sin respuesta |
| 5 | `job_email_lote2` | Lun-Vie 12:00 | Segunda tanda email |
| 6 | `job_batch2` (WA) | Lun-Vie 15:00 | Segunda tanda WhatsApp |
| 7 | `job_email_lote3` | Lun-Vie 16:00 | Tercera tanda email |
| 8 | `job_batch3` (WA) | Lun-Vie 17:30 | Tercera tanda WhatsApp |
| 9 | `job_email_followup` | Cada 2 horas | Re-envío emails sin respuesta |
| 10 | `job_inbox_monitor` | Cada 30 min | Lee Gmail, marca leads que respondieron |
| 11 | `job_wa_seguimiento` | Cada 2 horas | Recordatorios 24h/72h |
| 12 | `job_fidelizacion` | Lunes 11:00 | Fidelización sellers por etapa |

### Verificación pendiente
- [ ] Confirmar que los 12 jobs corren efectivamente en Railway (revisar `job_runs` productiva)
- [ ] Detectar jobs que fallan silenciosamente (sin error visible pero sin trabajo realizado)
- [ ] Validar que `job_auto_scraping` produce leads efectivamente (último lead nuevo, fecha)

---

## 4. Plan de trabajo — 4 fases

### Fase 1 — Auditoría (esta semana)
- [x] Diagnóstico inicial · este documento
- [ ] Conectar a Railway y verificar ejecuciones reales de jobs últimos 7 días
- [ ] Validar integridad BD productiva vs local
- [ ] Verificar estado Evolution API real
- [ ] Decidir: ¿el flujo email se completa o se desactiva la UI?

### Fase 2 — Reparación (1-2 semanas)
- [ ] Resolver `et_sends = 0`: completar flujo email O ocultar pestaña hasta que funcione
- [ ] Bot WA: mover a rama `feature/wa-bot-experimental` · sacar de main hasta que esté listo
- [ ] Limpiar archivos legacy (`app_pythonanywhere.py`, scripts `check_*.py`, `fix_*.py`)
- [ ] Auditar mensajes "huerfanos" en `wa_messages` sin lead asociado

### Fase 3 — Hardening (1 semana)
- [ ] Implementar backup automático BD Railway → repo privado cifrado o S3
- [ ] Validación HMAC en webhook de Evolution (CWE-345)
- [ ] Rotar todas las API keys de servicios externos (Anthropic, OpenAI, Apify, Brave, Google CSE)
- [ ] Evaluar reemplazo de `MP_FAST_PASSWORD` por token de sesión rotable
- [ ] Escribir `README.md` técnico (setup local, deploy Railway, troubleshooting)

### Fase 4 — Documentación para jefatura (3-4 días)
- [ ] One-pager refrescado con estado real
- [ ] `ARCHITECTURE.md` para evaluación de Engineering
- [ ] Lista de "qué decide jefatura": features a mantener / eliminar / integrar con sistemas oficiales

---

## 5. Decisiones pendientes que dependen de jefatura

Cuando se presente el proyecto, estas son las decisiones que solo jefatura puede tomar:

1. **¿Migrar a Fury?** — Engineering define el sponsor y las directrices
2. **¿Mantener bot WA con Evolution o esperar canal oficial via `iam_soporte_rrss`?**
3. **¿Usar Mail Service interno para notificaciones internas (hand-off, reportería)?**
4. **¿Integrar con Vambe / Gus Chat / Salesforce** (BSPs ya conectados al BSA de MP)?
5. **¿Email prospección externa con SMTP actual o gestionar acceso a servicio aprobado por Seguridad?**
6. **¿`MP_FAST_PASSWORD` es legítimo seguir usándolo o se busca acceso a Fast vía API documentada?**

---

## 6. Histórico de cambios al sistema

| Fecha | Cambio | Commit |
|---|---|---|
| 2026-04-17 | Versión 1.0 funcional · sistema base | `fd620f9` |
| 2026-05-09 | Fix duplicate /webhook route bloqueando bot | `4416d60` |
| 2026-05-09 | Fix v2 nested webhook payload Evolution | `8966776` |
| 2026-05-09 | Fix flat v2 webhook payload | `1e57b75` |
| 2026-05-09 | Diagnóstico dual-casing events + inspect endpoint | `30c16a9` |
| 2026-05-15 | Rotación token GitHub · limpieza `.git/config` | (sin commit · solo config local) |

---

*Próxima actualización del documento: al cerrar Fase 1 (validación Railway real).*
