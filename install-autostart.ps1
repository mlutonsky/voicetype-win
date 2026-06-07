# Enable autostart at login (a shortcut in the Startup folder).
# Disable: delete the shortcut in  shell:startup  (Win+R -> shell:startup).
$ErrorActionPreference = 'Stop'
$base = Split-Path -Parent $MyInvocation.MyCommand.Path
$vbs = Join-Path $base 'start-dictation.vbs'
if (-not (Test-Path $vbs)) { Write-Error "start-dictation.vbs not found in $base"; exit 1 }

$startup = [Environment]::GetFolderPath('Startup')
$lnk = Join-Path $startup 'voicetype-win.lnk'
$ws = New-Object -ComObject WScript.Shell
$sc = $ws.CreateShortcut($lnk)
$sc.TargetPath = 'wscript.exe'
$sc.Arguments = '"' + $vbs + '"'
$sc.WorkingDirectory = $base
$sc.Description = 'voicetype-win - local voice dictation'
$sc.Save()
Write-Host "Autostart enabled: $lnk" -ForegroundColor Green
