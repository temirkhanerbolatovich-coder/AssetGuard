#!/usr/bin/env bash
# Installs the AssetGuard production monitor as a systemd timer.
set -euo pipefail

project_dir="/opt/assetguard"
source_script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/assetguard-server-monitor.sh"
config_file="/etc/assetguard/server-monitor.env"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) project_dir="$2"; shift 2 ;;
    --config) config_file="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$source_script" ]] || { echo "Monitor script was not found: $source_script" >&2; exit 1; }
sudo install -d -m 700 /etc/assetguard
if [[ ! -f "$config_file" ]]; then
  sudo tee "$config_file" >/dev/null <<'EOF'
# Add both values, then keep this file readable only by root.
ASSETGUARD_TELEGRAM_BOT_TOKEN=
ASSETGUARD_TELEGRAM_CHAT_ID=
# Written by the production backup job after every successful R2 upload.
ASSETGUARD_BACKUP_STATUS_FILE=/var/lib/assetguard/backup-status.env
EOF
fi
sudo chmod 600 "$config_file"
sudo install -m 700 "$source_script" /usr/local/lib/assetguard-server-monitor.sh

sudo tee /etc/systemd/system/assetguard-monitor.service >/dev/null <<EOF
[Unit]
Description=AssetGuard production health monitor
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/assetguard-server-monitor.sh --project-dir $project_dir --config $config_file
EOF

sudo tee /etc/systemd/system/assetguard-monitor.timer >/dev/null <<'EOF'
[Unit]
Description=Run AssetGuard production monitor every five minutes

[Timer]
OnBootSec=3min
OnUnitActiveSec=5min
Persistent=true

[Install]
WantedBy=timers.target
EOF

sudo systemctl daemon-reload
sudo systemctl enable --now assetguard-monitor.timer
echo "Installed assetguard-monitor.timer. Configure $config_file before the first successful notification."
