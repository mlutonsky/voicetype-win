@echo off
REM Zapne automaticke spusteni po prihlaseni (staci dvojklik).
REM -ExecutionPolicy Bypass plati jen pro toto spusteni, nemeni systemove nastaveni.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-autostart.ps1"
echo.
pause
