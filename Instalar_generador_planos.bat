@echo off
chcp 65001 >nul
setlocal
rem Instala una sola vez el generador local de planos TT300-C (Modo 2 del módulo «Planos»).
rem Busca Python 3.12 o 3.11, crea el entorno .venv-planos junto a este archivo e instala requirements-planos.txt.
cd /d "%~dp0"
title Instalar generador de planos TT300-C
echo.
echo  Instalación del generador local de planos TT300-C
echo  =================================================
echo.
set "PY="
call :probar py -3.12
if defined PY goto encontrado
call :probar py -3.11
if defined PY goto encontrado
call :probar python
if defined PY goto encontrado
echo  No se encontró Python 3.12 ni 3.11 en este equipo.
echo.
echo  Descárguelo e instálelo desde https://www.python.org/downloads/windows/
echo  (versión 3.12 de 64 bits; marque "Add python.exe to PATH" en el instalador)
echo  y vuelva a ejecutar Instalar_generador_planos.bat.
echo.
pause
exit /b 1

:encontrado
echo  Python encontrado: %PY%
if exist ".venv-planos\Scripts\python.exe" goto instalar
echo  Creando el entorno .venv-planos ...
%PY% -m venv .venv-planos
if errorlevel 1 goto error

:instalar
echo  Instalando paquetes (cadquery, ezdxf, pymupdf, ...). Puede tardar varios minutos y descargar ~1 GB.
".venv-planos\Scripts\python.exe" -m pip install --upgrade pip
if errorlevel 1 goto error
".venv-planos\Scripts\python.exe" -m pip install -r requirements-planos.txt
if errorlevel 1 goto error
".venv-planos\Scripts\python.exe" -c "import cadquery, ezdxf, pymupdf, shapely, openpyxl, PIL, pypdf; print('  Paquetes verificados.')"
if errorlevel 1 goto error
echo.
echo  Instalación lista. Para generar planos ejecute Generar_planos_Tornamesa.bat
echo.
pause
exit /b 0

:error
echo.
echo  ERROR: la instalación no terminó. Revise el mensaje anterior (conexión a internet, espacio en disco o versión de Python).
echo  Puede borrar la carpeta .venv-planos y volver a ejecutar este archivo.
echo.
pause
exit /b 1

:probar
%* -c "import sys; sys.exit(0 if sys.version_info[:2] in ((3, 12), (3, 11)) else 1)" >nul 2>&1
if not errorlevel 1 set "PY=%*"
exit /b 0
