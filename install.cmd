@echo off
REM ============================================================================
REM  voicetype-win - installer (just double-click this file).
REM  It only runs install.ps1 (which creates the venv and installs dependencies).
REM
REM  About "-ExecutionPolicy Bypass" on the next line - it is NOT dangerous:
REM    * By default Windows refuses to run unsigned local .ps1 scripts. This flag
REM      lifts that restriction ONLY for this one command / this one process.
REM    * It does NOT change any system-wide or persistent setting - the moment
REM      this window closes, nothing about your machine has changed.
REM    * "-NoProfile" just skips your personal PowerShell profile for a clean run.
REM  In short: this line saves you from typing that command by hand. You can read
REM  install.ps1 first - it is a short, plain-text script.
REM ============================================================================
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0install.ps1" %*
echo.
pause
