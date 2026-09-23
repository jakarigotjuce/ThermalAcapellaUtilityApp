@echo off
cd /d "%~dp0"
".venv\Scripts\python.exe" -m pip install --upgrade "yt-dlp[default]"
pause
