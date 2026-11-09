@echo off
rem Starts CampusMind (Ollama, backend, app) and opens it in the browser.
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\start.ps1" %*
if errorlevel 1 pause
