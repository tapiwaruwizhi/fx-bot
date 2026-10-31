<#
  Stops the FX bot (launcher + backend). The MT5 terminal is left running.
  Usage:  powershell -ExecutionPolicy Bypass -File scripts\stop-bot.ps1
#>
Stop-ScheduledTask -TaskName "FX Bot" -ErrorAction SilentlyContinue

$procs = Get-CimInstance Win32_Process |
    Where-Object { $_.CommandLine -and ($_.CommandLine -like "*start-bot.ps1*" -or $_.CommandLine -like "*run_bot.py*") }

if (-not $procs) {
    Write-Host "FX bot is not running."
} else {
    foreach ($p in $procs) {
        Stop-Process -Id $p.ProcessId -Force -ErrorAction SilentlyContinue
        Write-Host ("Stopped {0} (PID {1})" -f $p.Name, $p.ProcessId)
    }
}
