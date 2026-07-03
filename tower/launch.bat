@echo off
title AIS-OS Control Tower
cd /d "%~dp0.."
echo Starting AIS-OS Control Tower...
python tower/start.py --no-reload
pause
