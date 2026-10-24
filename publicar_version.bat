@echo off
setlocal enabledelayedexpansion
title Publicador de Actualizaciones - buscaapps.com/youtube
cd /d "%~dp0"

echo ========================================================
echo   Publicador de Descargador de YouTube a buscaapps.com
echo ========================================================
echo.

if not exist "version.json" (
    echo [ERROR] No se encuentra el archivo version.json.
    pause
    exit /b 1
)

if not exist "YouTubeDownloader.zip" (
    echo [ERROR] No se encuentra YouTubeDownloader.zip.
    echo Ejecuta primero compilar.bat para generar el paquete ZIP.
    pause
    exit /b 1
)

echo Mostrando informacion del paquete a publicar:
findstr /i "version date url" version.json
echo.

set "WINSCP_EXE=C:\Program Files (x86)\WinSCP\WinSCP.com"
if not exist "%WINSCP_EXE%" (
    set "WINSCP_EXE=C:\Program Files\WinSCP\WinSCP.com"
)

if not exist "%WINSCP_EXE%" (
    echo [ERROR] No se encontro WinSCP.com en las rutas habituales.
    pause
    exit /b 1
)

echo Se subiran los siguientes archivos a buscaapps.com/youtube/:
echo   1. YouTubeDownloader.zip (paquete portable)
echo   2. version.json (manifiesto de version)
echo   3. index.html (pagina web de presentacion y descarga)
echo.
set /p RESP="¿Deseas iniciar la subida con WinSCP ahora? (S/N): "
if /i not "%RESP%"=="S" (
    echo Subida cancelada por el usuario.
    pause
    exit /b 0
)

echo.
echo Conectando con buscaapps mediante WinSCP y subiendo archivos...
echo (Este proceso puede tardar unos minutos dependiendo de la velocidad de subida)
echo.

"%WINSCP_EXE%" /command ^
    "open buscaapps" ^
    "cd /buscaapps.com/youtube" ^
    "put YouTubeDownloader.zip" ^
    "put version.json" ^
    "put index.html" ^
    "exit"

if %ERRORLEVEL% EQU 0 (
    echo.
    echo ========================================================
    echo   [EXITO] Archivos subidos correctamente.
    echo   Ya disponibles en:
    echo     - https://buscaapps.com/youtube/version.json
    echo     - https://buscaapps.com/youtube/YouTubeDownloader.zip
    echo ========================================================
) else (
    echo.
    echo [ERROR] Ocurrio un error durante la subida con WinSCP.
)

pause
