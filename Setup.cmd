@echo off
cd /d "%~dp0"
powershell.exe -NoProfile -ExecutionPolicy Bypass -File "%~dp0setup.ps1"
if errorlevel 1 (
  echo Setup did not finish. See the error above.
) else (
  echo Setup complete. Open Acapella Downloader on your desktop.
)
pause
