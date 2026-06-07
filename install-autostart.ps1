# Zapne automatické spuštění po přihlášení (zástupce ve složce Po spuštění).
# Vypnutí: smaž zástupce ve  shell:startup  (Win+R -> shell:startup).
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs = Join-Path $base 'start-dictation.vbs'
if (-not (Test-Path $vbs)) { Write-Error "start-dictation.vbs nenalezen v $base"; exit 1 }

$startup = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $startup 'voicetype-win.lnk'
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
$sc.TargetPath = 'wscript.exe'
$sc.Arguments = '"' + $vbs + '"'
$sc.WorkingDirectory = $base
$sc.Description = 'voicetype-win - lokalni hlasove diktovani'
$sc.Save()
Write-Host "Autostart zapnut: $lnk" -ForegroundColor Green
