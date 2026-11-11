@echo off
cd /d "%~dp0"
python build.py
if errorlevel 1 (echo Build failed & pause & exit /b 1)
echo Ready: dist\SeaBattle.exe
pause
