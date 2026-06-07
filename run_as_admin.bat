@echo off
cd /d "%~dp0"
set "SCRIPT=%~dp0studylock.py"
powershell -NoProfile -ExecutionPolicy Bypass -Command "Start-Process -FilePath 'py' -ArgumentList @('-3', $env:SCRIPT) -Verb RunAs"
