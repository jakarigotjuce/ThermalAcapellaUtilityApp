@echo off
setlocal
set "acapellaInstall=%LOCALAPPDATA%\Programs\AcapellaDownloader"
if not exist "%acapellaInstall%\.venv\Scripts\python.exe" (
  echo The app is not installed yet. Run Setup.cmd first.
  pause
  exit /b 1
)
echo Close Acapella Downloader before continuing.
pause
copy /y "%acapellaInstall%\app.py" "%acapellaInstall%\app.previous.py" >nul
if errorlevel 1 (
  echo Could not back up the installed interface. No update was applied.
  pause
  exit /b 1
)
copy /y "%~dp0app.py" "%acapellaInstall%\app.py" >nul
if errorlevel 1 (
  echo Could not update the interface.
  pause
  exit /b 1
)
echo Thermal interface installed. Open your usual desktop shortcut.
pause
