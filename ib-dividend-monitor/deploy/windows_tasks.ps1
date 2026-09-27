# Registra las tareas en el Programador de tareas de Windows.
# Ejecútalo en PowerShell desde la carpeta del proyecto:  powershell -ExecutionPolicy Bypass -File deploy\windows_tasks.ps1
$Project = (Resolve-Path "$PSScriptRoot\..").Path
$Divmon  = Join-Path $Project ".venv\Scripts\divmon.exe"

function Register-Divmon($Name, $Arguments, $Trigger) {
    $Action   = New-ScheduledTaskAction -Execute $Divmon -Argument $Arguments -WorkingDirectory $Project
    # Si el PC estaba apagado a la hora prevista, se ejecuta en cuanto se encienda.
    $Settings = New-ScheduledTaskSettingsSet -StartWhenAvailable -ExecutionTimeLimit (New-TimeSpan -Minutes 30)
    Register-ScheduledTask -TaskName $Name -Action $Action -Trigger $Trigger -Settings $Settings -Force | Out-Null
    Write-Host "Tarea registrada: $Name"
}

Register-Divmon "divmon - diario" "daily" `
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Tuesday,Wednesday,Thursday,Friday,Saturday -At 07:40)

Register-Divmon "divmon - informe semanal" "report --send" `
    (New-ScheduledTaskTrigger -Weekly -DaysOfWeek Saturday -At 09:10)

# Solo con IB Gateway activado: margen cada 30 minutos entre las 9:00 y las 22:00.
# $t = New-ScheduledTaskTrigger -Daily -At 09:00
# $t.Repetition = (New-ScheduledTaskTrigger -Once -At 09:00 -RepetitionInterval (New-TimeSpan -Minutes 30) -RepetitionDuration (New-TimeSpan -Hours 13)).Repetition
# Register-Divmon "divmon - margen en vivo" "margin-live" $t
