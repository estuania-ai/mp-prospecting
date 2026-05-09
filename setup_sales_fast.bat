@echo off
chcp 65001 >nul
setlocal enabledelayedexpansion

REM ════════════════════════════════════════════════════════════════
REM  SETUP_SALES_FAST.bat
REM  Onboarding one-shot para Sales/TL: instala deps, configura .env,
REM  hace login MP, deja todo listo para correr start_fast.bat.
REM
REM  Uso: doble-click o desde CMD: setup_sales_fast.bat
REM ════════════════════════════════════════════════════════════════

echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   MP Prospecting · Setup Multi-Fast para Sales/TL          ║
echo ║   Conecta tu PC al sistema para registrar leads en Fast    ║
echo ╚════════════════════════════════════════════════════════════╝
echo.

REM ── 1. Verificar Python ──────────────────────────────────────────
echo [1/6] Verificando Python...
python --version >nul 2>&1
if errorlevel 1 (
    echo ❌ Python no encontrado. Instalalo desde https://www.python.org/downloads/
    echo    Marcá "Add Python to PATH" durante la instalación.
    pause
    exit /b 1
)
for /f "tokens=2" %%i in ('python --version') do set PYVER=%%i
echo ✓ Python !PYVER! detectado
echo.

REM ── 2. Instalar dependencias ─────────────────────────────────────
echo [2/6] Instalando dependencias (esto tarda 1-2 min la primera vez)...
python -m pip install --quiet --upgrade pip 2>nul
python -m pip install --quiet -r requirements.txt
if errorlevel 1 (
    echo ⚠️  pip install falló. Probá ejecutar como Administrador.
    pause
    exit /b 1
)
echo ✓ Dependencias OK
echo.

REM ── 3. Instalar Playwright Chromium ──────────────────────────────
echo [3/6] Instalando Chromium para Playwright...
python -m playwright install chromium >nul 2>&1
echo ✓ Chromium listo
echo.

REM ── 4. Crear .env si no existe ──────────────────────────────────
echo [4/6] Configurando .env...
if exist .env (
    echo    .env ya existe. ¿Querés sobreescribirlo? (s/N)
    set /p OVERWRITE=
    if /i not "!OVERWRITE!"=="s" (
        echo    Manteniendo .env actual.
        goto :env_done
    )
)

echo.
echo    Ingresá tus credenciales de MP Fast (las usás en mercadopago.cl/fast):
set /p MP_EMAIL="    Email MP: "
set /p MP_PASS="    Password MP: "

REM Generar FAST_LOCAL_TOKEN aleatorio (64 chars hex)
for /f "delims=" %%i in ('python -c "import secrets; print(secrets.token_hex(32))"') do set FAST_TOKEN=%%i

(
    echo # MP Fast credentials
    echo MP_FAST_EMAIL=!MP_EMAIL!
    echo MP_FAST_PASSWORD=!MP_PASS!
    echo.
    echo # Token compartido — pegalo idéntico en Mi Perfil → Mi Fast
    echo FAST_LOCAL_TOKEN=!FAST_TOKEN!
    echo.
    echo # Puerto local (no cambies salvo conflicto^)
    echo FAST_LOCAL_PORT=5050
) > .env
echo ✓ .env creado con tus credenciales y un token nuevo
echo.

:env_done

REM ── 5. Login manual MP Fast ─────────────────────────────────────
echo [5/6] Login manual a MP Fast...
echo    Se va a abrir Chromium. Logueate con tu cuenta MP.
echo    Cuando estés en el dashboard de Fast, cerrá el navegador.
echo.
pause
python fast_login_manual.py
if errorlevel 1 (
    echo ⚠️  Login falló o lo cancelaste. Podés reintentar con: python fast_login_manual.py
)
echo ✓ Sesión MP guardada
echo.

REM ── 6. Mostrar el token para Mi Perfil ──────────────────────────
echo [6/6] Token compartido para tu perfil:
echo.
for /f "tokens=2 delims==" %%i in ('findstr /b "FAST_LOCAL_TOKEN=" .env') do echo    !!!  %%i  !!!
echo.
echo ╔════════════════════════════════════════════════════════════╗
echo ║   PRÓXIMOS PASOS                                           ║
echo ╠════════════════════════════════════════════════════════════╣
echo ║                                                            ║
echo ║   1. Ejecutá:  start_fast.bat                              ║
echo ║      (deja la ventana abierta mientras trabajes)           ║
echo ║                                                            ║
echo ║   2. Copiá la URL https://*.trycloudflare.com que aparece  ║
echo ║      después de "Your quick tunnel"                        ║
echo ║                                                            ║
echo ║   3. En el dashboard web → Mi Perfil → Mi Fast:            ║
echo ║      - URL pública: pegá la del tunnel                     ║
echo ║      - Token: pegá el FAST_LOCAL_TOKEN de arriba           ║
echo ║      - Guardar + Probar conexión                           ║
echo ║                                                            ║
echo ╚════════════════════════════════════════════════════════════╝
echo.
echo Setup completo ✓
pause
