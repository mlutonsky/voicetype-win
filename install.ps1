# voicetype-win – instalace závislostí do .venv
# Spuštění:  powershell -ExecutionPolicy Bypass -File install.ps1
#   -Cpu     instalace bez NVIDIA GPU (CPU-only)
param([switch]$Cpu)

$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
Set-Location $base

Write-Host "== voicetype-win install ==" -ForegroundColor Cyan

# 1) Najdi Python 3.11 (doporučeno) nebo jiný python3
$pyExe = $null
if (Get-Command py -ErrorAction SilentlyContinue) {
    try { & py -3.11 --version *> $null; if ($?) { $pyExe = 'py -3.11' } } catch {}
    if (-not $pyExe) { try { & py -3 --version *> $null; if ($?) { $pyExe = 'py -3' } } catch {} }
}
if (-not $pyExe -and (Get-Command python -ErrorAction SilentlyContinue)) { $pyExe = 'python' }
if (-not $pyExe) {
    Write-Error "Python nenalezen. Nainstaluj Python 3.11: winget install Python.Python.3.11"
    exit 1
}
Write-Host "Python: $pyExe" -ForegroundColor Green

# 2) Vytvoř venv
if (-not (Test-Path "$base\.venv")) {
    Write-Host "Vytvářím .venv ..."
    Invoke-Expression "$pyExe -m venv `"$base\.venv`""
}
$venvPy = "$base\.venv\Scripts\python.exe"

# 3) Instalace závislostí
& $venvPy -m pip install --upgrade pip
$req = if ($Cpu) { 'requirements-cpu.txt' } else { 'requirements.txt' }
Write-Host "Instaluji $req (může chvíli trvat – stahuje se i CUDA runtime) ..." -ForegroundColor Cyan
& $venvPy -m pip install -r "$base\$req"

Write-Host ""
Write-Host "Hotovo. Ověření GPU/modelu:  .\.venv\Scripts\python.exe smoke_test.py" -ForegroundColor Green
Write-Host "Spuštění na pozadí:          dvojklik na start-dictation.vbs" -ForegroundColor Green
Write-Host "Autostart po přihlášení:     powershell -ExecutionPolicy Bypass -File install-autostart.ps1" -ForegroundColor Green
