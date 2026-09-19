@echo off
cd /d "%~dp0"
if not exist ".venv\Scripts\python.exe" (
  echo Virtual environment not found.
  echo Run: python -m venv .venv
  echo Then: .venv\Scripts\activate
  echo Then: pip install -r requirements.txt
  pause
  exit /b 1
)
call .venv\Scripts\activate
python app.py
pause
