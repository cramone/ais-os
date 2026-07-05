@echo off
title Deploy Tower to Cortex
cd /d "%~dp0.."
echo Deploying AIS-OS Control Tower to Cortex...
echo You may be prompted for your SSH password/key passphrase.
echo.
ssh chase@cortex "cd /mnt/shared/claudia/magiq && ./tower/deploy-cortex.sh"
echo.
echo Done. Press any key to close.
pause >nul
