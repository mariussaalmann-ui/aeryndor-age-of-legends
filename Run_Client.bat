@echo off
cd /d "%~dp0"
if exist "%~dp0AeryndorLauncher.exe" (
  start "" "%~dp0AeryndorLauncher.exe"
) else (
  start "" "%~dp0AeryndorClient.exe"
)
