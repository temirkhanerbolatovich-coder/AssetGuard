#!/usr/bin/env bash
# Restores the latest production R2 backup into an isolated disposable PostgreSQL container.
set -euo pipefail
project_dir="/opt/assetguard"
config_file="/etc/assetguard/server-backup.env"
while [[ $# -gt 0 ]]; do case "$1" in --project-dir) project_dir="$2"; shift 2;; --config) config_file="$2"; shift 2;; *) exit 2;; esac; done
value() { sed -n "s/^$1=//p" "$2" | tail -n 1 | sed 's/\r$//'; }
config_file="$(readlink -f "$config_file")"
target="$(value ASSETGUARD_R2_TARGET "$config_file")"; passphrase="$(value ASSETGUARD_BACKUP_PASSPHRASE "$config_file")"
status="/var/lib/assetguard/backup-status.env"; name="$(value ASSETGUARD_BACKUP_OBJECT "$status")"
crypto="/usr/local/lib/assetguard/assetguard-backup-crypto.py"
[[ "$name" =~ ^assetguard-production-[0-9]{8}-[0-9]{6}\.sql\.agbackup$ && -n "$target" && -n "$passphrase" ]] || { echo 'Backup configuration or status is invalid.' >&2; exit 1; }
stage="$(mktemp -d /var/lib/assetguard/restore.XXXXXX)"; container="assetguard-restore-${RANDOM}${RANDOM}"
trap 'docker rm -f "$container" >/dev/null 2>&1 || true; rm -rf "$stage"' EXIT
rclone copyto "$target/$name" "$stage/$name"
printf '%s\n' "$passphrase" | "$crypto" decrypt --input "$stage/$name" --output "$stage/restore.sql" --passphrase-stdin
[[ -s "$stage/restore.sql" ]] || { echo 'Decryption produced an empty SQL file.' >&2; exit 1; }
password="$(openssl rand -base64 24)"
docker run -d --rm --name "$container" -e POSTGRES_DB=restore -e POSTGRES_USER=restore -e "POSTGRES_PASSWORD=$password" postgres:17-alpine >/dev/null
for _ in {1..30}; do docker exec "$container" psql -U restore -d restore -c 'SELECT 1' >/dev/null 2>&1 && break; sleep 2; done
docker exec "$container" psql -U restore -d restore -c 'SELECT 1' >/dev/null
docker exec -i "$container" psql -v ON_ERROR_STOP=1 -U restore -d restore <"$stage/restore.sql" >/dev/null
result="$(docker exec "$container" psql -At -U restore -d restore -c "SELECT 'revision=' || version_num FROM alembic_version UNION ALL SELECT 'assets=' || count(*) FROM assets UNION ALL SELECT 'endpoints=' || count(*) FROM managed_endpoints;")"
echo "Off-site restore rehearsal PASS: $name"
echo "$result"
