# MP Prospecting - Sistema de Prospección WhatsApp para MercadoPago

## Descripción
Sistema de prospección comercial automatizado via WhatsApp Desktop para vendedores de POS MercadoPago. Permite gestionar leads, enviar mensajes de prospección personalizados, hacer seguimiento de prospectos interesados y fidelizar sellers.

## Stack Tecnológico
- **Backend:** Python 3.11 + Flask
- **Base de datos:** SQLite
- **Frontend:** HTML/CSS/JavaScript vanilla
- **WhatsApp:** pyautogui (automatización WhatsApp Desktop)
- **Scraping:** Apify (Google Maps Extractor)

## Requisitos
- Python 3.11+
- WhatsApp Desktop instalado y con sesión activa
- Token Apify (para scraping de leads)

## Instalación
```bash
pip install -r requirements.txt
python app.py
```
Abrir: http://localhost:5000

## Estructura del Proyecto
```
mp_prospecting/
├── app.py                    # Aplicacion Flask principal
├── apify_scraper.py          # Scraping Google Maps via Apify
├── database.py               # Conexion y utilidades SQLite
├── rubros_config.py          # Configuracion rubros y mensajes
├── fidelizacion_config.py    # Mensajes por etapa de fidelizacion
├── scheduler_local.py        # Scheduler de envios automaticos
├── routes/
│   ├── leads.py              # API leads (CRUD + estados + importacion)
│   ├── sellers.py            # API sellers y fidelizacion
│   ├── campaigns.py          # API campanas y exportacion Excel
│   ├── dashboard.py          # API KPIs y metricas
│   ├── manual_send.py        # Envio manual de mensajes
│   ├── scraping.py           # API scraping Google Maps
│   ├── prospects.py          # API prospectos interesados y tareas
│   └── prospecting_intel.py  # API inteligencia de prospeccion
├── jobs/
│   ├── send_prospecting.py   # Job envio automatico prospeccion
│   ├── send_fidelizacion.py  # Job fidelizacion sellers
│   └── send_seguimiento.py   # Job seguimiento 24h/72h
├── whatsapp/
│   └── sender_desktop.py     # Sender WhatsApp Desktop via pyautogui
├── templates/
│   └── dashboard.html        # Dashboard principal
└── data/
    └── prospecting.db        # Base de datos SQLite
```

## Base de Datos
Tablas principales:
- **leads** — Prospectos con nombre, telefono, rubro, categoria, comuna
- **lead_status** — Estado de cada lead (no_enviado, enviado, interesado, cerrado, etc.)
- **messages** — Historial de mensajes enviados
- **sellers** — Sellers cerrados en proceso de fidelizacion
- **campaigns** — Campanas de envio registradas
- **prospects** — Prospectos interesados con info detallada
- **tasks** — Agenda de tareas por prospecto
- **importaciones** — Historial de archivos Excel importados
- **scraping_jobs** — Historial de scrapings ejecutados
- **config** — Configuracion del sistema (token Apify, horarios, etc.)
- **opt_out** — Lista negra de telefonos

## Funcionalidades

### Leads
- Estados: no_enviado, enviado, abierto, interesado, quiere_reunion, cerrado, no_interesado, opt_out
- Importacion masiva desde Excel (.xlsx) con columnas: Negocio, Telefono, Comuna, Rubro
- Exportacion CSV con todos los campos incluyendo motivos opt-out y seguimientos
- Reconocimiento fuzzy de rubros (tildes, mayusculas, errores tipograficos)
- Correccion masiva de rubros desconocidos
- Historial de archivos importados con opcion de eliminar (protegido con password)

### Mensajes
- Prospección automatica L-V: 09:30 (15 msgs), 15:00 (10 msgs), 17:30 (15 msgs)
- Seguimiento automatico: 24h y 72h para leads sin respuesta
- Fidelizacion sellers: dias 7, 14, 15, 30, 35 desde cierre
- Mensaje especial automatico para opt-out con motivo "Tiene MP"
- Mensajes personalizados por rubro con imagen segun categoria

### Rubros y Categorias
| Categoria | Rubros |
|-----------|--------|
| Comercio de Alta Demanda | Botilleria, Carniceria |
| Comercio de Barrio Diario | Almacen, Emporio, Fruteria, Minimarket, Panaderia, Verduleria |
| Gastronomia y Comida Rapida | Cafeteria, Fuente de Soda, Pizzeria, Sandwicheria, Sushi |
| Membresias y Entrenamientos | Gimnasio |
| Retail Especializado y Hogar | Bazar/Jugueteria, Ferreteria, Libreria, Muebleria |
| Salud y Farmacia | Farmacia |
| Servicios de Alto Ticket | Clinica Dental, Spa, Taller, Veterinaria |
| Servicios Personales Diario | Lavanderia, Peluqueria |

### Scraping
- Por rubro + comuna via Apify Google Maps Extractor
- Por link directo de Google Maps
- Extraccion automatica de comuna desde direccion
- Historial de scrapings con estadisticas
- Validacion automatica de token Apify al cambiar
- Actor configurable: `compass/google-maps-extractor` (ID guardado en config BD)

### Interesados
- Panel dedicado para prospectos en estado interesado
- Formulario completo: competencia, procedencia, notas
- Mensajes predefinidos WA (mas informacion, seguimiento)
- Agenda de tareas: llamada, reunion, seguimiento, visita terreno
- Calendario semanal
- Exportacion CSV de interesados

## Configuracion
Desde el dashboard en /configuracion:
- **Apify Token:** Token de cuenta Apify para scraping
- **Ejecutivo:** Nombre y telefono del vendedor
- **Horarios:** Hora de prospección y fidelizacion
- **Limites:** Mensajes por dia y delays entre mensajes

## WhatsApp - Limitacion Importante
El sistema usa **pyautogui** para controlar WhatsApp Desktop en Windows.
Esto significa:
- Solo funciona en el PC donde esta instalado WhatsApp Desktop
- La sesion de WhatsApp debe estar activa
- No funciona en servidores en la nube

**Para produccion en la nube se recomienda migrar a:**
- `whatsapp-web.js` (Node.js) — conexion via QR code
- WhatsApp Business API (Meta) — API oficial con costo

## Ambientes de Dashboard
- `/` — Dashboard principal estable
- `/test` a `/test12` — Ambientes de prueba (eliminar en produccion)

## Credenciales
- Password archivos importados: configurado en codigo (mp_fix_archivos_importados.py)
- No hay login de usuario actualmente — agregar autenticacion en produccion

## Notas para el Desarrollador
1. Migrar WhatsApp sender de pyautogui a whatsapp-web.js
2. Agregar autenticacion de usuario (login/logout)
3. Migrar SQLite a PostgreSQL para produccion
4. Configurar variables de entorno para tokens y passwords
5. Eliminar ambientes de test (/test1 al /test12) en produccion
6. El actor Apify puede variar segun la cuenta — verificar en config BD
