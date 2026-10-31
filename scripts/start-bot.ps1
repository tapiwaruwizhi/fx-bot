<#
  Starts the MT5 terminal (if it is not already running) and the FX bot
  backend. If the backend stops for any reason it is restarted after 30 s.

  Started at Windows logon by the "FX Bot" scheduled task
  (install with scripts\install-startup.ps1). Can also be run by hand.

  Log: backend\logs\bot-YYYY-MM-DD.log
#>
$ErrorActionPreference = "Continue"

$Root    = Split-Path -Parent $PSScriptRoot
$Backend = Join-Path $Root "backend"
$Python  = Join-Path $Backend ".venv\Scripts\python.exe"
$Runner  = Join-Path $Backend "run_bot.py"
$EnvFile = Join-Path $Backend ".env"
$LogDir  = Join-Path $Backend "logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null

function Get-LogPath { Join-Path $LogDir ("bot-{0:yyyy-MM-dd}.log" -f (Get-Date)) }

function Write-Log([string]$Message) {
    $line = "{0:yyyy-MM-dd HH:mm:ss}  [launcher] {1}" -f (Get-Date), $Message
    try { Add-Content -Path (Get-LogPath) -Value $line } catch { }
}

function Get-EnvValue([string]$Name) {
    if (-not (Test-Path $EnvFile)) { return "" }
    $line = Get-Content $EnvFile | Where-Object { $_ -match "^\s*$Name\s*=" } | Select-Object -First 1
    if (-not $line) { return "" }
    return ($line -replace "^\s*$Name\s*=\s*", "").Trim().Trim('"')
}

# Only one launcher at a time
$createdNew = $false
$mutex = New-Object System.Threading.Mutex($true, "Local\FxBotLauncher", [ref]$createdNew)
if (-not $createdNew) {
    Write-Log "Another launcher is already running; exiting."
    exit 0
}

if (-not (Test-Path $Python)) {
    Write-Log "Python not found at $Python - create the venv and install requirements first."
    exit 1
}

# Wait (up to 5 min) for the internet connection after boot
Write-Log "Waiting for network..."
for ($i = 0; $i -lt 60; $i++) {
    try { [System.Net.Dns]::GetHostAddresses("api.frankfurter.dev") | Out-Null; break }
    catch { Start-Sleep -Seconds 5 }
}

# Start the MT5 terminal so it can log in before the bot connects
if ((Get-EnvValue "MT5_ENABLED") -eq "true") {
    $mt5Path = Get-EnvValue "MT5_PATH"
    if ($mt5Path -and (Test-Path $mt5Path)) {
        $exeName = [System.IO.Path]::GetFileNameWithoutExtension($mt5Path)
        $running = Get-Process -Name $exeName -ErrorAction SilentlyContinue |
            Where-Object { $_.Path -eq $mt5Path }
        if ($running) {
            Write-Log "MT5 terminal already running."
        } else {
            Write-Log "Starting MT5 terminal: $mt5Path"
            Start-Process -FilePath $mt5Path
            Start-Sleep -Seconds 30
        }
    } else {
        Write-Log "MT5_PATH '$mt5Path' not found; the bot will try to start MT5 itself."
    }
}

$env:PYTHONUNBUFFERED = "1"
$env:PYTHONIOENCODING = "utf-8"
Set-Location $Backend

while ($true) {
    Write-Log "Starting backend."
    & $Python $Runner
    Write-Log "Backend stopped (exit code $LASTEXITCODE). Restarting in 30 seconds."
    Start-Sleep -Seconds 30
}
