@echo off

:: Verificar si el script se está ejecutando con privilegios de administrador
NET SESSION >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Este script necesita privilegios de administrador. Ejecutando con elevación...
    powershell -Command "Start-Process cmd -ArgumentList '/c %~dp0run_wot_adapter.bat' -Verb runAs"
    exit
)

:: Ruta relativa al archivo Python (si está en la misma carpeta que el .bat)
set PYTHON_SCRIPT="%~dp0wot-n7-adapter.py"

:: Verificar si Python está instalado
where python >nul 2>nul
IF %ERRORLEVEL% NEQ 0 (
    echo Python no esta instalado. Por favor, instale Python.
    pause
    exit /b
)

:: Ejecutar el archivo Python
echo Ejecutando el script Python...
python %PYTHON_SCRIPT%

:: Verificar si el script se ejecuto correctamente
IF %ERRORLEVEL% EQU 0 (
    echo El script se ejecuto correctamente.
) ELSE (
    echo Hubo un error al ejecutar el script.
)

:: Mantener la ventana abierta para ver el resultado
pause
