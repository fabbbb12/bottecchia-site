@echo off
setlocal

set SYMBOL=%1
if "%SYMBOL%"=="" set SYMBOL=BTCUSDT

cd /d "%~dp0"
set PYTHONPATH=.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo === Atualizando o projeto (git pull) ===
git pull
if errorlevel 1 (
    echo AVISO: git pull falhou -- seguindo com o codigo local mesmo assim.
)

echo.
echo === Rodando um ciclo do F2 ao vivo (%SYMBOL%) ===
python scripts\run_f2_live.py %SYMBOL%
if errorlevel 1 (
    echo ERRO ao rodar run_f2_live.py -- confira se o venv esta ativado e as dependencias instaladas.
    pause
    exit /b 1
)

echo.
echo === Gerando o dashboard ===
python scripts\f2_dashboard.py %SYMBOL%
if errorlevel 1 (
    echo ERRO ao gerar o dashboard.
    pause
    exit /b 1
)

set SAFE_SYMBOL=%SYMBOL:/=_%
start "" "state\f2_%SAFE_SYMBOL%_dashboard.html"

endlocal
