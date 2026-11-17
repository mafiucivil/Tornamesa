@echo off
chcp 65001 >nul
setlocal
rem Abre el generador local de planos TT300-C y la herramienta en el navegador (http://127.0.0.1:8765/).
cd /d "%~dp0"
title Generador de planos TT300-C
if not exist ".venv-planos\Scripts\python.exe" (
  echo.
  echo  El generador de planos no está instalado.
  echo  Ejecute primero Instalar_generador_planos.bat ^(una sola vez^).
  echo.
  pause
  exit /b 1
)
call ".venv-planos\Scripts\activate.bat"
set "PYTHONUTF8=1"
python tools\servidor_planos.py %*
if errorlevel 1 (
  echo.
  echo  El generador se detuvo con error. Revise el mensaje anterior.
  echo.
  pause
  exit /b 1
)
exit /b 0
