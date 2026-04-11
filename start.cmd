@echo off
cd /d "%~dp0"
call .\.venv\Scripts\activate.bat
echo.
echo [OK] venv activated in: %cd%
cmd /k
