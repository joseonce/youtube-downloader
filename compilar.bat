@echo off
title Compilando Descargador de YouTube
cd /d "%~dp0"

echo ========================================================
echo   Compilacion de Descargador de YouTube con PyInstaller
echo ========================================================
echo.

echo [1/3] Compilando ejecutable principal...
python -m PyInstaller --noconfirm YouTubeDownloader.spec
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo la compilacion con PyInstaller.
    pause
    exit /b %ERRORLEVEL%
)

echo.
echo [2/3] Sincronizando directorios y creando paquete ZIP...
python build_package.py
if %ERRORLEVEL% NEQ 0 (
    echo [ERROR] Fallo el empaquetado del proyecto.
    pause
    exit /b %ERRORLEVEL%
)


echo.
echo [3/3] Proceso finalizado correctamente.
echo El ejecutable y las dependencias portables estan listos en dist/ y en YouTubeDownloader.zip.
pause

