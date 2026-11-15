@echo off
REM Gera um unico .exe em dist\Desconversor.exe
REM Precisam estar ao lado do main.py: logo.png, clt_egogift.ico e a pasta Font

cd /d "%~dp0"

if not exist "logo.png" goto faltando
if not exist "clt_egogift.ico" goto faltando
if not exist "Font" goto faltando

python -m pip install pyinstaller
python -m PyInstaller --noconsole --onefile --name DesconversorCLT --collect-all customtkinter --icon clt_egogift.ico --add-data "logo.png;." --add-data "clt_egogift.ico;." --add-data "Font;Font" main.py
if errorlevel 1 goto erro

REM Limpa o lixo do build (so o .exe em dist fica)
if exist "build" rmdir /s /q "build"
if exist "Desconversor.spec" del /q "Desconversor.spec"
if exist "__pycache__" rmdir /s /q "__pycache__"
if exist "desconversor\__pycache__" rmdir /s /q "desconversor\__pycache__"

echo.
echo Pronto! O programa esta em dist\Desconversor.exe
pause
exit /b 0

:faltando
echo.
echo Faltam arquivos ao lado do build.bat. Precisam existir:
echo   logo.png, clt_egogift.ico e a pasta Font
pause
exit /b 1

:erro
echo.
echo O build falhou. Leia a mensagem de erro acima.
echo (As pastas temporarias foram mantidas para ajudar a achar o problema.)
pause
exit /b 1
