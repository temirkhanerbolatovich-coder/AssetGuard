#!/usr/bin/env bash
# Installs a daily encrypted production backup systemd timer. It stays disabled until configured.
set -euo pipefail

project_dir="/opt/assetguard"
source_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
config_file="/etc/assetguard/server-backup.env"

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) project_dir="$2"; shift 2 ;;
    --config) config_file="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

[[ -f "$source_dir/assetguard-server-backup.sh" && -f "$source_dir/assetguard-server-restore-rehearsal.sh" && -f "$source_dir/assetguard-backup-crypto.py" ]] || { echo 'Backup source files are missing.' >&2; exit 1; }
command -v docker >/dev/null || { echo 'Docker is required.' >&2; exit 1; }
command -v rclone >/dev/null || { echo 'rclone is required.' >&2; exit 1; }
python3 -c 'import cryptography' >/dev/null 2>&1 || { echo 'python3-cryptography is required (Ubuntu: sudo apt install python3-cryptography).' >&2; exit 1; }
sudo install -d -m 700 /etc/assetguard /var/lib/assetguard /usr/local/lib/assetguard
if [[ ! -f "$config_file" ]]; then
  sudo tee "$config_file" >/dev/null <<'EOF'
# Keep this file root-only. Do not store it in Git.
ASSETGUARD_BACKUP_PASSPHRASE=
ASSETGUARD_R2_TARGET=assetguard-r2:assetguard-backups/production
EOF
fi
sudo chmod 600 "$config_file"
sudo install -m 700 "$source_dir/assetguard-server-backup.sh" /usr/local/lib/assetguard-server-backup.sh
sudo install -m 700 "$source_dir/assetguard-server-restore-rehearsal.sh" /usr/local/lib/assetguard-server-restore-rehearsal.sh
sudo install -m 700 "$source_dir/assetguard-backup-crypto.py" /usr/local/lib/assetguard/assetguard-backup-crypto.py

sudo tee /etc/systemd/system/assetguard-backup.service >/dev/null <<EOF
[Unit]
Description=AssetGuard encrypted production backup to R2
After=docker.service network-online.target
Wants=network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/assetguard-server-backup.sh --project-dir $project_dir --config $config_file
EOF
sudo tee /etc/systemd/system/assetguard-backup.timer >/dev/null <<'EOF'
[Unit]
Description=Run AssetGuard production backup every day

[Timer]
OnCalendar=*-*-* 02:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo tee /etc/systemd/system/assetguard-restore-rehearsal.service >/dev/null <<EOF
[Unit]
Description=AssetGuard isolated off-site restore rehearsal
After=docker.service network-online.target

[Service]
Type=oneshot
ExecStart=/usr/local/lib/assetguard-server-restore-rehearsal.sh --project-dir $project_dir --config $config_file
EOF
sudo tee /etc/systemd/system/assetguard-restore-rehearsal.timer >/dev/null <<'EOF'
[Unit]
Description=Run AssetGuard off-site restore rehearsal weekly

[Timer]
OnCalendar=Sun *-*-* 03:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF
sudo systemctl daemon-reload
echo "Installed backup and restore-rehearsal timers. Configure $config_file and root rclone before enabling them."
