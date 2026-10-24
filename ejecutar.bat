@echo off
title Descargador de YouTube
cd /d "%~dp0"
echo Iniciando Descargador de YouTube...
python app.py
if %ERRORLEVEL% NEQ 0 (
    echo.
    echo Ocurrio un error al ejecutar la aplicacion (Codigo de salida: %ERRORLEVEL%).
    pause
)
