@echo off
start "" wsl.exe -d Ubuntu -- bash -c "bash ~/claudia-dashboard/start.sh &"
timeout /t 3 /nobreak >nul
start "" "http://localhost:7842"
