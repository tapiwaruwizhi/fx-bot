<#
  Registers a scheduled task "FX Bot" that runs scripts\start-bot.ps1
  1 minute after you log in to Windows.

  Install:    powershell -ExecutionPolicy Bypass -File scripts\install-startup.ps1
  Start now:  powershell -ExecutionPolicy Bypass -File scripts\install-startup.ps1 -StartNow
  Remove:     powershell -ExecutionPolicy Bypass -File scripts\install-startup.ps1 -Uninstall
#>
param(
    [switch]$Uninstall,
    [switch]$StartNow
)

$TaskName = "FX Bot"

if ($Uninstall) {
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Removed scheduled task '$TaskName'."
    exit 0
}

$Script = Join-Path $PSScriptRoot "start-bot.ps1"
$User   = "$env:USERDOMAIN\$env:USERNAME"

$action = New-ScheduledTaskAction -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -WindowStyle Hidden -File `"$Script`""

$trigger = New-ScheduledTaskTrigger -AtLogOn -User $User
$trigger.Delay = "PT1M"   # give Windows a minute to settle after login

$settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval (New-TimeSpan -Minutes 5) `
    -MultipleInstances IgnoreNew

# Interactive = runs in your desktop session, which the MT5 terminal needs
$principal = New-ScheduledTaskPrincipal -UserId $User -LogonType Interactive -RunLevel Limited

Register-ScheduledTask -TaskName $TaskName -Action $action -Trigger $trigger `
    -Settings $settings -Principal $principal -Force `
    -Description "Starts MT5 and the FX bot backend at logon" | Out-Null

Write-Host "Installed scheduled task '$TaskName' (runs at logon for $User)."

if ($StartNow) {
    Start-ScheduledTask -TaskName $TaskName
    Write-Host "Started. Log: backend\logs\bot-$(Get-Date -Format yyyy-MM-dd).log"
}
