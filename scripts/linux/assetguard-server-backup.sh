#!/usr/bin/env bash
# Creates an AES-256-GCM backup of the production database and uploads it to R2.
set -euo pipefail

project_dir="/opt/assetguard"
config_file="/etc/assetguard/server-backup.env"
retention_days=30

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) project_dir="$2"; shift 2 ;;
    --config) config_file="$2"; shift 2 ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

read_env_value() {
  local name="$1" file="$2"
  sed -n "s/^${name}=//p" "$file" | tail -n 1
}

project_env="$project_dir/.env"
compose_dir="$project_dir/infra/containers"
state_dir="/var/lib/assetguard"
backup_dir="$state_dir/backups"
status_file="$state_dir/backup-status.env"
crypto="/usr/local/lib/assetguard/assetguard-backup-crypto.py"

[[ -r "$project_env" && -r "$config_file" && -x "$crypto" ]] || { echo 'AssetGuard backup configuration is incomplete.' >&2; exit 1; }
database_user="$(read_env_value ASSETGUARD_POSTGRES_USER "$project_env")"
database_name="$(read_env_value ASSETGUARD_POSTGRES_DB "$project_env")"
passphrase="$(read_env_value ASSETGUARD_BACKUP_PASSPHRASE "$config_file")"
offsite_target="$(read_env_value ASSETGUARD_R2_TARGET "$config_file")"
[[ -n "$database_user" && -n "$database_name" && -n "$passphrase" && -n "$offsite_target" ]] || { echo 'Database, passphrase, or R2 target is not configured.' >&2; exit 1; }

install -d -m 700 "$backup_dir"
stage_dir="$(mktemp -d "$backup_dir/stage.XXXXXX")"
trap 'rm -rf "$stage_dir"' EXIT
timestamp="$(date -u +%Y%m%d-%H%M%S)"
name="assetguard-production-${timestamp}.sql.agbackup"
plain_sql="$stage_dir/database.sql"
encrypted_backup="$backup_dir/$name"

docker compose --env-file "$project_env" -f "$compose_dir/docker-compose.production.yml" -f "$compose_dir/docker-compose.oracle-free.yml" \
  exec -T postgres pg_dump -U "$database_user" -d "$database_name" --format=plain --no-owner >"$plain_sql"
[[ -s "$plain_sql" ]] || { echo 'Database dump is empty.' >&2; exit 1; }

printf '%s\n' "$passphrase" | "$crypto" encrypt --input "$plain_sql" --output "$encrypted_backup" --passphrase-stdin
rclone copyto "$encrypted_backup" "$offsite_target/$name"
rclone delete "$offsite_target" --min-age "${retention_days}d"
find "$backup_dir" -maxdepth 1 -type f -name '*.agbackup' -mtime +13 -delete

umask 077
printf 'ASSETGUARD_BACKUP_SUCCESS_UNIX=%s\nASSETGUARD_BACKUP_OBJECT=%s\n' "$(date +%s)" "$name" >"$status_file"
echo "Encrypted production backup uploaded: $offsite_target/$name"
