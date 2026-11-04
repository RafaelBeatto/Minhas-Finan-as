@echo off
setlocal
cd /d "%~dp0"

rem Compila o front-end se a pasta dist ainda nao existir ou se passou "--build".
set PRECISA_BUILD=0
if not exist "dist\index.html" set PRECISA_BUILD=1
if /i "%~1"=="--build" set PRECISA_BUILD=1

if "%PRECISA_BUILD%"=="1" (
    where npm >nul 2>nul
    if errorlevel 1 (
        echo [aviso] npm nao encontrado; pulando a compilacao do front-end.
    ) else (
        if not exist "node_modules" call npm install
        echo Compilando o front-end...
        call npm run build
        if errorlevel 1 (
            echo [erro] A compilacao falhou.
            pause
            exit /b 1
        )
    )
)

cd /d "%~dp0finan-servidor"
python -m pip install -q -r requirements.txt
echo.
echo Finan em http://127.0.0.1:8766/finan
python servidor.py
pause
