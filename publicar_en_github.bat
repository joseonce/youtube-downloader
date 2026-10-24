@echo off
title Publicar en GitHub - Fuentes y Release ZIP
cd /d "%~dp0"

echo ========================================================
echo   Publicador Automatico a GitHub (joseonce/youtube-downloader)
echo ========================================================
echo.

echo [1/3] Preparando codigo fuente...
git add -A
git status --short

echo.
set /p MENSAJE="Escribe la descripcion del cambio para el commit (o pulsa Enter para automatico): "
if "%MENSAJE%"=="" set MENSAJE="Actualizacion automatica de version y mejoras"

echo.
echo [2/3] Creando commit y subiendo codigo fuente a GitHub (rama main)...
git commit -m "%MENSAJE%"
git push origin main

echo.
echo [3/3] Creando Release y subiendo YouTubeDownloader.zip a GitHub Releases...
python publicar_release_github.py

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [EXITO TOTAL] Fuentes y Release subidos a GitHub!
    echo   Repositorio: https://github.com/joseonce/youtube-downloader
    echo   Releases:    https://github.com/joseonce/youtube-downloader/releases
    echo ========================================================
) else (
    echo.
    echo [AVISO] Hubo un problema al subir la Release.
)

echo.
pause
