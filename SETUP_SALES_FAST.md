# 🚀 Setup Multi-Fast para Sales / TL

Guía paso a paso para conectar tu PC al sistema MP Prospecting y poder registrar leads en MercadoPago Fast con **tu propia cuenta**.

---

## ¿Qué hace esto?

Cuando registrás un lead en Fast desde el dashboard web, normalmente la automatización corre en la PC del Owner. Con Multi-Fast, **corre en tu propia PC con tus credenciales** — vos sos el comercial responsable y MP registra la visita a tu nombre.

**Cómo funciona:**

```
Dashboard Web (Railway)
        │
        │  POST /api/leads/X/registrar-fast
        ▼
   Railway resuelve:
   - "¿Quién es current_user?"
   - Si es Sales/TL con perfil configurado → enruta a TU PC
   - Si es Owner → enruta a la PC del Owner
        │
        ▼
   Cloudflare Tunnel
   https://abc-123.trycloudflare.com
        │
        ▼
   Tu PC (fast_local_server.py)
   con tus credenciales MP en .env
        │
        ▼
   Playwright → mercadopago.cl/fast
   Registra el lead a tu nombre ✓
```

---

## Requisitos

- 💻 **Windows** (estos scripts son `.bat`; en Mac/Linux usá los comandos sueltos).
- 🐍 **Python 3.10+** instalado con "Add to PATH" activado.
- 🌐 **Cloudflared** instalado (alternativa: ngrok).
- ✉️ Una cuenta de **MP Fast** activa (con la que ya iniciás sesión en mercadopago.cl).
- 📂 El repo del proyecto clonado/copiado en tu PC.

---

## Setup (una sola vez)

### 1. Clonar o copiar el proyecto

```powershell
git clone https://github.com/estuania-ai/mp-prospecting.git
cd mp-prospecting
```

O si no tenés git, pedí al Owner una copia del proyecto.

### 2. Instalar Cloudflared

**Opción A — winget (recomendado):**
```powershell
winget install --id Cloudflare.cloudflared
```

**Opción B — manual:**
1. Descargá `cloudflared-windows-amd64.exe` desde:
   https://github.com/cloudflare/cloudflared/releases/latest
2. Renombralo a `cloudflared.exe`.
3. Movelo a `C:\Windows\` o a una carpeta del `PATH`.

Verificá:
```powershell
cloudflared --version
```

### 3. Correr el setup automático

Doble-click sobre **`setup_sales_fast.bat`** o desde CMD:

```powershell
setup_sales_fast.bat
```

El script va a:
1. Verificar Python.
2. Instalar dependencias (`pip install -r requirements.txt`).
3. Instalar Chromium para Playwright.
4. Crear `.env` con tus credenciales MP y un `FAST_LOCAL_TOKEN` aleatorio fuerte.
5. Abrir Chromium para que loguées tu cuenta MP (la sesión queda guardada).
6. Mostrarte el token que tenés que pegar en el dashboard.

**Importante:** copiá el `FAST_LOCAL_TOKEN` que muestra al final.

### 4. Arrancar el server + tunnel

Doble-click **`start_fast.bat`** o:

```powershell
start_fast.bat
```

Se abren dos ventanas:
- **Fast Local Server** — corre en `localhost:5050`.
- **Cloudflare Tunnel** — expone tu PC a internet.

En la ventana del Tunnel vas a ver una línea como:
```
2026-05-09T10:00:00Z INF +--------------------------------------------------------------------------------------------+
2026-05-09T10:00:00Z INF |  Your quick tunnel has been created! Visit it at (it may take a few seconds):                 |
2026-05-09T10:00:00Z INF |  https://wonderful-trees-fly.trycloudflare.com                                                |
2026-05-09T10:00:00Z INF +--------------------------------------------------------------------------------------------+
```

**Copiá esa URL** (`https://wonderful-trees-fly.trycloudflare.com`).

### 5. Configurar en el dashboard

1. Andá al dashboard web → **Mi Perfil** → card **⚡ Mi Fast Registro**.
2. Pegá:
   - **URL pública**: la del tunnel (`https://wonderful-trees-fly.trycloudflare.com`).
   - **Token**: el `FAST_LOCAL_TOKEN` del paso 3.
3. Click **💾 Guardar**.
4. Click **🧪 Probar conexión** → debe decir **"✓ Conectividad OK · tunnel responde, token válido"**.

¡Listo! Ahora cuando registrés leads en Fast desde el dashboard, la automatización corre en tu PC.

---

## Uso diario

**Cada vez que querés trabajar:**
1. Doble-click `start_fast.bat`.
2. Esperá ~10 segundos a que aparezca la URL del tunnel.
3. **Si la URL cambió** (Cloudflare quick tunnels son temporales), copiá la nueva en Mi Perfil → Guardar.
4. Trabajá normal en el dashboard.

**Cuando termines:** Cerrá las dos ventanas con Ctrl+C.

---

## ⚠️ Sobre Cloudflare Quick Tunnels

Los `--url` quick tunnels que usa este script son **gratis pero la URL cambia** cada vez que reiniciás. Hay 2 alternativas más estables:

### Opción A: Quick tunnel (default, fácil)
- ✅ Gratis, sin registro.
- ❌ URL cambia cada arranque → tenés que actualizar Mi Perfil.

### Opción B: Named tunnel (recomendado para uso diario)
- Necesitás cuenta gratis de Cloudflare + dominio (puede ser de Cloudflare Free).
- URL fija (ej. `https://miusuario-fast.midominio.com`).
- Setup: https://developers.cloudflare.com/cloudflare-one/connections/connect-networks/get-started/create-local-tunnel/

### Opción C: ngrok
- Plan gratis: 1 tunnel persistente con URL fija.
- Reemplazá el comando `cloudflared` en `start_fast.bat` por:
  ```
  ngrok http 5050
  ```

---

## Troubleshooting

### "Token inválido en servidor local"
Significa que el token en Mi Perfil no coincide con el de tu `.env`.
- Abrí `C:\...\mp_prospecting\.env` con Notepad.
- Copiá el valor exacto de `FAST_LOCAL_TOKEN=...`.
- Pegalo en Mi Perfil → Mi Fast → Token → Guardar.

### "Servidor local Fast no disponible"
- Verificá que la ventana de "Fast Local Server" esté abierta y corriendo.
- Verificá que la URL del tunnel todavía esté activa (probá abrirla en el browser).
- Reiniciá `start_fast.bat`.

### "Auth fallida: 535 Username and Password not accepted"
- Tu password de MP Fast cambió. Editá `.env` y actualizá `MP_FAST_PASSWORD`.
- Reiniciá `start_fast.bat`.

### Botón "Probar conexión" da error
- Mirá los logs en la ventana de Fast Local Server — ahí aparece el error real.
- Si el server crashea, los stack traces están en esa misma ventana.

### Ya logueé manualmente pero pide login otra vez
- La sesión expiró. Corré `python fast_login_manual.py` de nuevo para refrescarla.

---

## Archivos importantes

| Archivo | Para qué |
|---|---|
| `.env` | Tus credenciales y tokens (NO commitear, NO compartir) |
| `data/fast_session.json` | Sesión MP guardada por Playwright |
| `fast_local_server.py` | El servidor Flask que corre en tu PC |
| `setup_sales_fast.bat` | Script de instalación (1 vez) |
| `start_fast.bat` | Script de arranque diario |

---

## Seguridad

🔐 **NO compartas tu `.env`** — contiene tu password MP y el token compartido.
🔐 **NO commitees `.env` a git** — ya está en `.gitignore` por defecto.
🔐 **El token se guarda encriptado** en la base de datos del dashboard.
🔐 **Renová el token periódicamente**: borralo del `.env`, corré `setup_sales_fast.bat` de nuevo, y actualizá Mi Perfil.

---

## ¿Dudas?

Pregúntale al Owner del sistema.
