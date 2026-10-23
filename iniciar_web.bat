@echo off
title Aegis-Quant Web Studio (http://localhost:8080)
echo ============================================================================
echo   Iniciando Aegis-Quant Web Studio en http://localhost:8080 ...
echo ============================================================================
start http://localhost:8080
python "%~dp0web_app\server.py"
pause
