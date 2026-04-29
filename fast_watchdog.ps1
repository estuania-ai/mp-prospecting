# Watchdog Fast: garantiza que servidor local + tunel esten corriendo.
# Si alguno cae, lo relanza. Se ejecuta cada 1 minuto via Task Scheduler.

$projectDir  = "C:\Users\juanspinto\mp_prospecting"
$cloudflared = "C:\Users\juanspinto\AppData\Local\Microsoft\WinGet\Packages\Cloudflare.cloudflared_Microsoft.Winget.Source_8wekyb3d8bbwe\cloudflared.exe"
$token       = "mp-fast-2026-secret"

# 1) Verificar Flask local en puerto 5050
$flaskOk = $false
try {
    $r = Invoke-WebRequest -Uri "http://localhost:5050/health" -TimeoutSec 3 -UseBasicParsing -ErrorAction Stop
    if ($r.StatusCode -eq 200) { $flaskOk = $true }
} catch { $flaskOk = $false }

if (-not $flaskOk) {
    # Matar cualquier python residual del servidor
    Get-Process python,pythonw -ErrorAction SilentlyContinue | Where-Object {
        try { ($_.CommandLine -like "*fast_local_server*") } catch { $false }
    } | Stop-Process -Force -ErrorAction SilentlyContinue

    # Lanzar oculto con pythonw (sin ventana). Las env vars se heredan del proceso padre.
    $env:FAST_LOCAL_TOKEN = $token
    $env:FAST_HEADLESS = "false"
    Start-Process -FilePath "pythonw.exe" `
        -ArgumentList "fast_local_server.py" `
        -WorkingDirectory $projectDir `
        -WindowStyle Hidden
    "$([DateTime]::Now.ToString('s')) - Flask relanzado" | Add-Content "$projectDir\logs\fast_watchdog.log"
}

# 2) Verificar cloudflared
$cfRunning = (Get-Process cloudflared -ErrorAction SilentlyContinue).Count -gt 0
if (-not $cfRunning) {
    Start-Process -FilePath $cloudflared `
        -ArgumentList "tunnel","run","fast-mp" `
        -WindowStyle Hidden
    "$([DateTime]::Now.ToString('s')) - Cloudflared relanzado" | Add-Content "$projectDir\logs\fast_watchdog.log"
}
