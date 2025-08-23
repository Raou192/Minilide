@echo off
cd /d "%~dp0"
python interface.py
choice /t 10 /d y /n >nul

exit
