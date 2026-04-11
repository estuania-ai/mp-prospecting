# setup_tasks.ps1
# Crea las 3 tareas programadas en Windows Task Scheduler
# Ejecutar como Administrador

$python = (Get-Command python).Source
$scriptDir = "C:\Users\juanspinto\mp_prospecting"
$script = "$scriptDir\run_batch.py"
$logDir = "$scriptDir\logs"

# Crear carpeta logs si no existe
if (-not (Test-Path $logDir)) { New-Item -ItemType Directory -Path $logDir }

Write-Host "Python: $python"
Write-Host "Script: $script"
Write-Host ""

# Funcion para crear tarea
function Create-BatchTask {
    param($name, $hour, $minute, $batch)

    $action  = New-ScheduledTaskAction -Execute $python -Argument "$script $batch" -WorkingDirectory $scriptDir
    $trigger = New-ScheduledTaskTrigger -Weekly -DaysOfWeek Monday,Tuesday,Wednesday,Thursday,Friday -At "$($hour):$($minute)"
    $settings= New-ScheduledTaskSettingsSet -ExecutionTimeLimit (New-TimeSpan -Minutes 30) -RestartCount 1 -RestartInterval (New-TimeSpan -Minutes 5)
    $principal = New-ScheduledTaskPrincipal -UserId $env:USERNAME -LogonType Interactive -RunLevel Limited

    # Eliminar si ya existe
    Unregister-ScheduledTask -TaskName $name -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask -TaskName $name -Action $action -Trigger $trigger -Settings $settings -Principal $principal -Description "MP Prospecting - Lote $batch"

    Write-Host "Tarea creada: $name -> $($hour):$($minute) (Lote $batch, $batch mensajes)"
}

Write-Host "=== Creando tareas de prospeccion MP ==="
Create-BatchTask "MP_Prospeccion_0930" "09" "30" "1"
Create-BatchTask "MP_Prospeccion_1500" "15" "00" "2"
Create-BatchTask "MP_Prospeccion_1730" "17" "30" "3"

Write-Host ""
Write-Host "=== Tareas creadas exitosamente ==="
Write-Host "Verificando..."
Get-ScheduledTask | Where-Object {$_.TaskName -like "MP_*"} | Select-Object TaskName, State | Format-Table
Write-Host ""
Write-Host "IMPORTANTE: WhatsApp Desktop debe estar abierto antes de cada envio"
