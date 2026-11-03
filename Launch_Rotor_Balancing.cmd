@echo off
cd /d "%~dp0"
if not exist ".devvenv\Scripts\python.exe" (
  echo Local development environment not found. See README.md for setup.
  pause
  exit /b 1
)
".devvenv\Scripts\python.exe" "Rotor_Balancing.py"
if errorlevel 1 pause
