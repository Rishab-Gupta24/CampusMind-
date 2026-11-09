@echo off
rem Stops the CampusMind backend and app (Ollama keeps running).
powershell -NoProfile -ExecutionPolicy Bypass -File "%~dp0scripts\stop.ps1"
pause
