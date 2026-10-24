@echo off
title Subiendo proyecto a GitHub - joseonce/youtube-downloader
cd /d "%~dp0"

echo ========================================================
echo   Subiendo Descargador de YouTube a GitHub
echo   Repositorio: https://github.com/joseonce/youtube-downloader
echo ========================================================
echo.
echo Ejecutando git push...
echo (Si es la primera vez, se abrira una ventana de tu navegador para autorizar la conexion)
echo.

git push -u origin main

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [EXITO] Proyecto subido correctamente a GitHub!
    echo   Puedes verlo en: https://github.com/joseonce/youtube-downloader
    echo ========================================================
) else (
    echo.
    echo [ERROR] Hubo un problema al subir a GitHub.
)

echo.
pause
