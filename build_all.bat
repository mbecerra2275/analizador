@echo off
REM =====================================================
REM Build completo: Ejecutable + Instalador
REM =====================================================
echo [1/4] Compilando ejecutable con PyInstaller...
python build_exe.py
if %errorlevel% neq 0 (
    echo [ERROR] Fallo compilación
    pause
    exit /b 1
)

echo.
echo [2/4] Verificando ejecutable...
if not exist "dist\LogAnalyzer.exe" (
    echo [ERROR] No se generó LogAnalyzer.exe
    pause
    exit /b 1
)
echo [OK] LogAnalyzer.exe generado (%~z dist\LogAnalyzer.exe bytes)

echo.
echo [3/4] Copiando archivos para instalador...
if not exist "dist" mkdir dist
copy dist\LogAnalyzer.exe dist\LogAnalyzer.exe >nul
copy scripts\install_deps.bat dist\install_deps.bat >nul
copy README_USUARIO.md dist\README_USUARIO.md >nul

echo.
echo [4/4] Compilando instalador Inno Setup...
REM Requiere Inno Setup instalado: https://jrsoftware.org/isdl.php
where iscc >nul 2>nul
if %errorlevel% neq 0 (
    echo [WARN] Inno Setup no encontrado (iscc)
    echo      Instale desde: https://jrsoftware.org/isdl.php
    echo.
    echo [OK] Ejecutable listo en: dist\LogAnalyzer.exe
    echo      Para crear instalador .exe instale Inno Setup y ejecute: iscc installer.iss
    pause
    exit /b 0
)

iscc installer.iss
if %errorlevel% neq 0 (
    echo [ERROR] Fallo compilación instalador
    pause
    exit /b 1
)

echo.
echo =============================================
echo [EXITO] Build completado!
echo =============================================
echo.
echo Instalador: dist_installer\LogAnalyzer_Setup_v1.0.0.exe
echo Ejecutable: dist\LogAnalyzer.exe
echo.
pause