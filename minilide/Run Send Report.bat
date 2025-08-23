@echo off
cd /d "%~dp0"
python send_report.py
choice /t 10 /d y /n >nul

exit
