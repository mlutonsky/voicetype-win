@echo off
REM voicetype-win - instalace (staci dvojklik).
REM Spusti install.ps1. Prepinac -ExecutionPolicy Bypass plati POUZE pro toto jedno
REM spusteni a NEMENI zadne systemove nastaveni - jen obejde vychozi blokaci
REM nepodepsanych skriptu, aby slo instalator spustit. install.cmd to dela za vas.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
