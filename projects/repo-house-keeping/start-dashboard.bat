@echo off
setlocal
title Repo House Keeping - Dashboard Server
rem Double-click to start the live dashboard and open it in your browser.
rem Close this window (or press Ctrl+C) to stop the server.
pushd "%~dp0"
where py >nul 2>nul
if %errorlevel%==0 (
  py -3 scripts\serve_dashboard.py %*
  goto :finished
)
where python >nul 2>nul
if %errorlevel%==0 (
  python scripts\serve_dashboard.py %*
  goto :finished
)
echo.
echo Python 3 was not found on PATH. Install it from python.org (tick "Add to PATH") and try again.
pause
:finished
if errorlevel 1 pause
popd
endlocal
