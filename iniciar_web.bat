@echo off
title Aegis-Quant Web Studio (http://localhost:8085)
echo ============================================================================
echo   Iniciando Aegis-Quant Web Studio en http://localhost:8085 ...
echo ============================================================================
start http://localhost:8085
python "%~dp0web_app\server.py" 8085
pause
