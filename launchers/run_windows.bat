@echo off
cd /d "%~dp0.."
if not exist venv (
    echo Virtual environment not found. Please run install instructions first.
    pause
    exit /b
)
call venv\Scripts\activate
python main.py
pause
