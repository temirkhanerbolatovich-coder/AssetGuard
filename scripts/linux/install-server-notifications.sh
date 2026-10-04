#!/usr/bin/env bash
# Uses the established deployment layout and keeps secrets outside the service unit.
set -euo pipefail
project_dir="${1:-/opt/assetguard}"
source_script="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/assetguard-server-notifications.sh"
sudo test -r /etc/assetguard/server-monitor.env
sudo chmod 600 /etc/assetguard/server-monitor.env
sudo install -m 700 "$source_script" /usr/local/lib/assetguard-server-notifications.sh
sudo tee /etc/systemd/system/assetguard-notifications.service >/dev/null <<EOF
[Unit]
Description=AssetGuard durable incident notifications
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
TimeoutStartSec=90
ExecStart=/usr/local/lib/assetguard-server-notifications.sh --project-dir $project_dir
EOF
sudo tee /etc/systemd/system/assetguard-notifications.timer >/dev/null <<'EOF'
[Unit]
Description=Deliver AssetGuard incident notifications every minute

[Timer]
OnBootSec=2min
OnUnitActiveSec=1min
AccuracySec=5s
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
sudo systemctl enable --now assetguard-notifications.timer
echo 'Installed assetguard-notifications.timer; organization scope must be configured in server-monitor.env.'
