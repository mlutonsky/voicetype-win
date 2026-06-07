# voicetype-win - install dependencies into .venv
# Easiest: double-click install.cmd
# From a terminal:  powershell -ExecutionPolicy Bypass -File install.ps1
#   -Cpu     force the CPU build (otherwise the GPU is auto-detected)
#
# Note on "-ExecutionPolicy Bypass": it is harmless here. Windows blocks unsigned
# local .ps1 scripts by default; the flag lifts that ONLY for that single command
# and changes no system-wide setting. It is just so this script can run at all.
param([switch]$Cpu)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base

Write-Host "== voicetype-win install ==" -ForegroundColor Cyan

# 1) Find Python 3.11 (recommended) or another python3
$pyExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try { & py -3.11 --version *> $null; if ($?) { $pyExe = 'py -3.11' } } catch {}
    if (-not $pyExe) { try { & py -3 --version *> $null; if ($?) { $pyExe = 'py -3' } } catch {} }
}
if (-not $pyExe -and (Get-Command python -ErrorAction SilentlyContinue)) { $pyExe = 'python' }
if (-not $pyExe) {
    Write-Error "Python not found. Install Python 3.11:  winget install Python.Python.3.11"
    exit 1
}
Write-Host "Python: $pyExe" -ForegroundColor Green

# 2) Create venv
if (-not (Test-Path "$base\.venv")) {
    Write-Host "Creating .venv ..."
    Invoke-Expression "$pyExe -m venv `"$base\.venv`""
}
$venvPy = "$base\.venv\Scripts\python.exe"

# 3) Auto-detect GPU - if no NVIDIA GPU and -Cpu was not given, use the CPU build
if (-not $Cpu) {
    $hasGpu = $false
    try { & nvidia-smi *> $null; if ($LASTEXITCODE -eq 0) { $hasGpu = $true } } catch {}
    if (-not $hasGpu) {
        Write-Host "No NVIDIA GPU detected - installing the CPU build (set device = cpu in config.toml)." -ForegroundColor Yellow
        $Cpu = $true
    } else {
        Write-Host "NVIDIA GPU detected - installing the GPU build." -ForegroundColor Green
    }
}

# 4) Install dependencies
& $venvPy -m pip install --upgrade pip
$req = if ($Cpu) { 'requirements-cpu.txt' } else { 'requirements.txt' }
Write-Host "Installing $req (may take a while - the GPU build also downloads the CUDA runtime) ..." -ForegroundColor Cyan
& $venvPy -m pip install -r "$base\$req"

Write-Host ""
Write-Host "Done. Verify GPU/model:   .\.venv\Scripts\python.exe smoke_test.py" -ForegroundColor Green
Write-Host "Run in background:        double-click start-dictation.vbs" -ForegroundColor Green
Write-Host "Autostart at login:       double-click install-autostart.cmd" -ForegroundColor Green
