@echo off
setlocal
cd /d "%~dp0"

REM If File -> Open Common Data Folder is not the usual AppData path,
REM uncomment the next line and point it at the MT4Copier folder
REM (the folder that contains master_status.json).
REM set MT4_COPIER_DIR=%APPDATA%\MetaQuotes\Terminal\Common\Files\MT4Copier

echo MT4 local trade copier
echo When this window prints the UI address, open http://127.0.0.1:8765
echo.

where py >nul 2>&1
if %errorlevel%==0 (
  py -3 -m app %*
  goto stopped
)
where python >nul 2>&1
if %errorlevel%==0 (
  python -m app %*
  goto stopped
)
echo Python 3 was not found.
echo Install Python 3 from https://www.python.org/downloads/
echo and check "Add python.exe to PATH", then run this file again.
:stopped
echo.
pause
