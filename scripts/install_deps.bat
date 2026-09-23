@echo off
REM =====================================================
REM Instalador de dependencias para Log Analyzer
REM Se ejecuta silenciosamente durante la instalación
REM =====================================================

setlocal enabledelayedexpansion

echo =============================================
echo  Log Analyzer - Instalando dependencias
echo =============================================
echo.

REM -------------------------------------------------
REM Función: Verificar si un comando existe
REM -------------------------------------------------
:check_cmd
where %1 >nul 2>nul
if %errorlevel% equ 0 (
    echo [OK] %1 ya instalado
    exit /b 0
) else (
    echo [--] %1 no encontrado, instalando...
    exit /b 1
)

REM -------------------------------------------------
REM 1. Verificar/instalar Ollama
REM -------------------------------------------------
call :check_cmd ollama
if %errorlevel% equ 1 (
    echo Instalando Ollama via winget...
    winget install Ollama.Ollama --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Ollama instalado
    ) else (
        echo [WARN] Error instalando Ollama. Instale manualmente: https://ollama.ai
    )
)

REM -------------------------------------------------
REM 2. Descargar modelo IA (requiere Ollama corriendo)
REM -------------------------------------------------
if exist "%LOCALAPPDATA%\Ollama\ollama.exe" (
    echo Iniciando servicio Ollama...
    start /b "" "%LOCALAPPDATA%\Ollama\ollama.exe" serve >nul 2>&1
    timeout /t 5 >nul
    
    echo Descargando modelo qwen2.5-coder:1.5b (aprox 1.5 GB)...
    "%LOCALAPPDATA%\Ollama\ollama.exe" pull qwen2.5-coder:1.5b
    if %errorlevel% equ 0 (
        echo [OK] Modelo IA descargado
    ) else (
        echo [WARN] Error descargando modelo. Ejecute manualmente: ollama pull qwen2.5-coder:1.5b
    )
    
    REM Detener servidor temporal
    taskkill /f /im ollama.exe >nul 2>&1
) else if exist "%PROGRAMFILES%\Ollama\ollama.exe" (
    echo Iniciando servicio Ollama...
    start /b "" "%PROGRAMFILES%\Ollama\ollama.exe" serve >nul 2>&1
    timeout /t 5 >nul
    
    echo Descargando modelo qwen2.5-coder:1.5b (aprox 1.5 GB)...
    "%PROGRAMFILES%\Ollama\ollama.exe" pull qwen2.5-coder:1.5b
    if %errorlevel% equ 0 (
        echo [OK] Modelo IA descargado
    ) else (
        echo [WARN] Error descargando modelo. Ejecute manualmente: ollama pull qwen2.5-coder:1.5b
    )
    
    taskkill /f /im ollama.exe >nul 2>&1
) else (
    echo [WARN] Ollama no encontrado en rutas estándar. Descargue modelo manualmente.
)

REM -------------------------------------------------
REM 3. Verificar/instalar Graphviz
REM -------------------------------------------------
call :check_cmd dot
if %errorlevel% equ 1 (
    echo Instalando Graphviz via winget...
    winget install Graphviz.Graphviz --silent --accept-source-agreements --accept-package-agreements >nul 2>&1
    if %errorlevel% equ 0 (
        echo [OK] Graphviz instalado
        REM Agregar al PATH del usuario actual
        setx PATH "%PATH%;C:\Program Files\Graphviz\bin" >nul 2>&1
    ) else (
        echo [WARN] Error instalando Graphviz. Los diagramas PNG no estarán disponibles.
    )
)

REM -------------------------------------------------
REM 4. Crear directorios de la aplicación
REM -------------------------------------------------
set APP_DIR=%~dp0
if not exist "%APP_DIR%output\reports" mkdir "%APP_DIR%output\reports" >nul 2>&1
if not exist "%APP_DIR%logs" mkdir "%APP_DIR%logs" >nul 2>&1
if not exist "%APP_DIR%config\rules" mkdir "%APP_DIR%config\rules" >nul 2>&1

REM -------------------------------------------------
REM 5. Agregar Graphviz al PATH permanente (opcional)
REM -------------------------------------------------
if exist "C:\Program Files\Graphviz\bin\dot.exe" (
    setx PATH "%PATH%;C:\Program Files\Graphviz\bin" >nul 2>&1
) else if exist "C:\Program Files (x86)\Graphviz\bin\dot.exe" (
    setx PATH "%PATH%;C:\Program Files (x86)\Graphviz\bin" >nul 2>&1
)

echo.
echo =============================================
echo  Instalación de dependencias completada
echo =============================================
echo.
echo Para usar Log Analyzer:
echo   1. Ejecute LogAnalyzer.exe
echo   2. Seleccione un archivo .log
echo   3. Haga clic en "Iniciar Análisis"
echo.
echo Notas:
echo - Ollama debe estar corriendo para análisis con IA
echo - Inicie Ollama: ollama serve
echo - Primer análisis descargará modelo (~1.5 GB)
echo.
pause
exit /b 0