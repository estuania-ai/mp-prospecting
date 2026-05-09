@echo off
chcp 65001 >nul

REM ════════════════════════════════════════════════════════════════
REM  start_fast.bat — Arranca tu Fast local + tunnel Cloudflare
REM
REM  Doble-click cada vez que querés trabajar. Dejá la ventana abierta.
REM  Para cerrar: Ctrl+C en cada ventana.
REM ════════════════════════════════════════════════════════════════

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   MP Prospecting · Iniciando tu Fast local                 ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM Verificar .env
if not exist .env (
    echo ❌ No existe .env. Corré primero:  setup_sales_fast.bat
    pause
    exit /b 1
)

REM Verificar cloudflared
where cloudflared >nul 2>&1
if errorlevel 1 (
    echo ⚠️  cloudflared no encontrado en el PATH.
    echo.
    echo    Instalalo desde: https://github.com/cloudflare/cloudflared/releases
    echo    Bajá: cloudflared-windows-amd64.exe
    echo    Renombralo a cloudflared.exe y ponelo en C:\Windows o en PATH.
    echo.
    echo    Alternativa rápida ^(si tenés winget^):
    echo       winget install --id Cloudflare.cloudflared
    echo.
    pause
    exit /b 1
)

REM ── Iniciar fast_local_server en ventana 1 ──────────────────────
echo [1/2] Arrancando fast_local_server (puerto 5050)...
start "Fast Local Server" cmd /k "python fast_local_server.py"
echo ✓ Server corriendo en otra ventana

REM Esperar a que el server esté listo
timeout /t 4 /nobreak >nul

REM Verificar health local
curl -s -o nul -w "%%{http_code}" http://127.0.0.1:5050/health > .health_check.tmp 2>nul
set /p HC=<.health_check.tmp
del .health_check.tmp 2>nul

if not "!HC!"=="200" (
    echo ⚠️  Server local no respondió en /health. Revisá la ventana del server.
    timeout /t 5 /nobreak >nul
)

REM ── Iniciar tunnel Cloudflare en ventana 2 ──────────────────────
echo.
echo [2/2] Abriendo tunnel Cloudflare...
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   IMPORTANTE: la URL pública aparece en la otra ventana.   ║
echo ║   Buscá la línea que dice:                                 ║
echo ║     "https://[algo-aleatorio].trycloudflare.com"           ║
echo ║   Esa es la URL que pegás en Mi Perfil → Mi Fast.          ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
start "Cloudflare Tunnel" cmd /k "cloudflared tunnel --url http://localhost:5050"

echo.
echo ✓ Todo arrancando. Dejá ambas ventanas abiertas mientras trabajes.
echo.
echo Para detener: cerrá las dos ventanas con Ctrl+C.
echo.
pause
