@echo off
setlocal enabledelayedexpansion

set SYMBOLS=%*
if "%SYMBOLS%"=="" set SYMBOLS=BTCUSDT ETHUSDT

cd /d "%~dp0"
set PYTHONPATH=.

if exist ".venv\Scripts\activate.bat" (
    call ".venv\Scripts\activate.bat"
)

echo === Atualizando o projeto - git pull ===
git pull
if errorlevel 1 (
    echo AVISO: git pull falhou -- seguindo com o codigo local mesmo assim.
)

for %%S in (%SYMBOLS%) do (
    echo.
    echo === Rodando um ciclo do F2 ao vivo - %%S ===
    python scripts\run_f2_live.py %%S
    if errorlevel 1 (
        echo ERRO ao rodar run_f2_live.py pra %%S -- confira se o venv esta ativado e as dependencias instaladas.
        pause
        exit /b 1
    )

    echo.
    echo === Gerando o dashboard - %%S ===
    python scripts\f2_dashboard.py %%S
    if errorlevel 1 (
        echo ERRO ao gerar o dashboard pra %%S.
        pause
        exit /b 1
    )

    set "SAFE_SYMBOL=%%S"
    set "SAFE_SYMBOL=!SAFE_SYMBOL:/=_!"
    start "" "state\f2_!SAFE_SYMBOL!_dashboard.html"
)

endlocal
