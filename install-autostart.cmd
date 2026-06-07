@echo off
REM ============================================================================
REM  voicetype-win - enable autostart at login (just double-click this file).
REM  It only runs install-autostart.ps1, which creates a shortcut in the
REM  Windows Startup folder. Disable later by deleting that shortcut
REM  (Win+R -> shell:startup).
REM
REM  About "-ExecutionPolicy Bypass" on the next line - it is NOT dangerous:
REM    * Windows blocks unsigned local .ps1 scripts by default; this flag lifts
REM      that ONLY for this one command / process and changes NO system setting.
REM    * "-NoProfile" just skips your personal PowerShell profile for a clean run.
REM  It simply saves you from typing the command by hand.
REM ============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install-autostart.ps1"
echo.
pause
