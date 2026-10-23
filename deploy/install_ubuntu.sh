#!/usr/bin/env bash
# ==============================================================================
# Instalador Automático 24/7 para Ubuntu Server + Tailscale VPN
# Proyecto: Aegis-Quant Web Studio & Paper Trading Bot
# Uso en tu Ubuntu Server:
#   sudo bash deploy/install_ubuntu.sh
# ==============================================================================

set -e

PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
RUN_USER="${SUDO_USER:-$USER}"
SERVICE_FILE="/etc/systemd/system/aegis-quant.service"

echo "=============================================================================="
echo " Instalando Aegis-Quant Studio como Servicio 24/7 en Ubuntu Server"
echo " Directorio del proyecto: ${PROJECT_DIR}"
echo " Usuario de ejecución   : ${RUN_USER}"
echo "=============================================================================="

# 1. Crear unidad systemd con auto-reinicio ante cortes de luz o caídas
cat <<EOF > "${SERVICE_FILE}"
[Unit]
Description=Aegis-Quant Paper Trading Bot & Web Control Center
After=network-online.target tailscaled.service
Wants=network-online.target

[Service]
Type=simple
User=${RUN_USER}
WorkingDirectory=${PROJECT_DIR}
ExecStart=/usr/bin/python3 ${PROJECT_DIR}/web_app/server.py
Restart=always
RestartSec=5
Environment=PYTHONUNBUFFERED=1

[Install]
WantedBy=multi-user.target
EOF

# 2. Recargar systemd, habilitar arranque automático y levantar el bot
systemctl daemon-reload
systemctl enable aegis-quant.service
systemctl restart aegis-quant.service

# 3. Detectar IP privada de Tailscale si está instalado
TS_IP=""
if command -v tailscale >/dev/null 2>&1; then
    TS_IP=$(tailscale ip -4 2>/dev/null || true)
fi
LOCAL_IP=$(hostname -I | awk '{print $1}')

echo ""
echo "✅ SERVICIO AEGIS-QUANT ACTIVO Y BLINDADO (Auto-arranque activado)"
echo "------------------------------------------------------------------------------"
echo " 🌐 Acceso en Red Local : http://${LOCAL_IP}:8080"
if [ -n "${TS_IP}" ]; then
    echo " 📱 Acceso Móvil VPN Tailscale: http://${TS_IP}:8080"
    echo " 🔒 (Opcional) Para activar HTTPS en Tailscale ejecuta:"
    echo "    sudo tailscale serve --bg 8080"
fi
echo "------------------------------------------------------------------------------"
echo " Comandos útiles en Ubuntu:"
echo "   Ver estado en vivo : sudo systemctl status aegis-quant"
echo "   Ver logs del motor : sudo journalctl -u aegis-quant -f"
echo "=============================================================================="
