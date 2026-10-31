@echo off
cd /d "%~dp0finan-servidor"
python -m pip install -q -r requirements.txt
python servidor.py
pause
