@echo off
cd /d "%~dp0"
echo Activating venv...
call .venv\Scripts\activate.bat
echo Running reposnapshot.py...
python reposnapshot.py
echo.
pause
