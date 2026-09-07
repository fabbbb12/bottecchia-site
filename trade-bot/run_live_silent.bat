@echo off
setlocal

set SYMBOLS=BTCUSDT ETHUSDT
cd /d "%~dp0"
set PYTHONPATH=.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

set LOGFILE=state\live_log.txt
if not exist state mkdir state

echo. >> "%LOGFILE%"
echo ===== %date% %time% ===== >> "%LOGFILE%"

git pull >> "%LOGFILE%" 2>&1

for %%S in (%SYMBOLS%) do (
    echo -- %%S -- >> "%LOGFILE%"
    python scripts\run_f2_live.py %%S >> "%LOGFILE%" 2>&1
    python scripts\f2_dashboard.py %%S >> "%LOGFILE%" 2>&1
)

endlocal
