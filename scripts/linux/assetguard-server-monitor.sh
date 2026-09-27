#!/usr/bin/env bash
# Checks AssetGuard production health and sends deduplicated Telegram alerts.
set -euo pipefail

project_dir="/opt/assetguard"
config_file="/etc/assetguard/server-monitor.env"
repeat_after_seconds=14400
minimum_free_percent=10
maximum_backup_age_hours=26
test_alert=false

while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) project_dir="$2"; shift 2 ;;
    --config) config_file="$2"; shift 2 ;;
    --test-alert) test_alert=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done

read_env_value() {
  local name="$1" file="$2"
  sed -n "s/^${name}=//p" "$file" | tail -n 1 | sed 's/\r$//'
}

project_env="$project_dir/.env"
compose_dir="$project_dir/infra/containers"
state_dir="/var/lib/assetguard-monitor"
state_file="$state_dir/state"

[[ -r "$project_env" ]] || { echo "Missing production environment file: $project_env" >&2; exit 1; }
[[ -r "$config_file" ]] || { echo "Missing monitor configuration: $config_file" >&2; exit 1; }

public_host="$(read_env_value ASSETGUARD_PUBLIC_HOST "$project_env")"
admin_token="$(read_env_value ASSETGUARD_ADMIN_SHARED_SECRET "$project_env")"
telegram_token="$(read_env_value ASSETGUARD_TELEGRAM_BOT_TOKEN "$config_file")"
telegram_chat_id="$(read_env_value ASSETGUARD_TELEGRAM_CHAT_ID "$config_file")"
backup_status_file="$(read_env_value ASSETGUARD_BACKUP_STATUS_FILE "$config_file")"
backup_status_file="${backup_status_file:-/var/lib/assetguard/backup-status.env}"

[[ -n "$public_host" && -n "$admin_token" ]] || { echo "Production URL or admin secret is not configured." >&2; exit 1; }
[[ -n "$telegram_token" && -n "$telegram_chat_id" ]] || { echo "Telegram monitor credentials are not configured." >&2; exit 1; }

problems=()
if [[ "$test_alert" == true ]]; then
  problems+=("TEST ONLY: Telegram alert delivery check; production remains online")
fi

if ! curl --fail --silent --show-error --max-time 20 "https://${public_host}/health/ready" >/dev/null; then
  problems+=("API readiness endpoint is unavailable")
fi

expected_services=(postgres api caddy)
running_services="$(docker compose --env-file "$project_env" -f "$compose_dir/docker-compose.production.yml" -f "$compose_dir/docker-compose.oracle-free.yml" ps --status running --services 2>/dev/null || true)"
for service in "${expected_services[@]}"; do
  if ! grep -qx "$service" <<<"$running_services"; then
    problems+=("Compose service is not running: $service")
  fi
done

for service in assetguard-backup.service assetguard-restore-rehearsal.service; do
  if systemctl is-failed --quiet "$service"; then
    problems+=("Systemd job failed: $service")
  fi
done

free_percent="$(df -P / | awk 'NR == 2 { print 100 - $5 }')"
if [[ "$free_percent" -lt "$minimum_free_percent" ]]; then
  problems+=("Low server disk space: ${free_percent}% free")
fi

if [[ ! -r "$backup_status_file" ]]; then
  problems+=("No server-side backup status file")
else
  backup_success_unix="$(read_env_value ASSETGUARD_BACKUP_SUCCESS_UNIX "$backup_status_file")"
  if [[ ! "$backup_success_unix" =~ ^[0-9]+$ ]]; then
    problems+=("Server-side backup status is invalid")
  else
    backup_age_hours=$(( ($(date +%s) - backup_success_unix) / 3600 ))
    if [[ "$backup_age_hours" -gt "$maximum_backup_age_hours" ]]; then
      problems+=("Latest server backup is ${backup_age_hours}h old")
    fi
  fi
fi

operations="$(curl --fail --silent --show-error --max-time 20 -H "X-AssetGuard-Admin-Token: $admin_token" "https://${public_host}/admin/operations/status" 2>/dev/null || true)"
if [[ -z "$operations" ]]; then
  problems+=("Operations API is unavailable")
else
  metrics="$(printf '%s' "$operations" | python3 -c '
import json, sys
data = json.load(sys.stdin)
agents = data.get("agents", {})
ingest = data.get("ingest", {})
print(int(agents.get("offline", 0)) + int(agents.get("stale", 0)), int(ingest.get("failed", 0)), int(agents.get("identity_conflicts", 0)))
')"
  read -r offline_agents failed_ingest identity_conflicts <<<"$metrics"
  [[ "$offline_agents" -eq 0 ]] || problems+=("Offline or stale agents: $offline_agents")
  [[ "$failed_ingest" -eq 0 ]] || problems+=("Failed inventory ingests: $failed_ingest")
  [[ "$identity_conflicts" -eq 0 ]] || problems+=("Endpoint identity conflicts: $identity_conflicts")
fi

if [[ ${#problems[@]} -eq 0 ]]; then
  echo "AssetGuard production checks passed."
  exit 0
fi

fingerprint="$(printf '%s\n' "${problems[@]}" | sha256sum | awk '{print $1}')"
now="$(date +%s)"
last_fingerprint=""
last_sent="0"
if [[ -r "$state_file" ]]; then
  last_fingerprint="$(read_env_value FINGERPRINT "$state_file")"
  last_sent="$(read_env_value LAST_SENT_UNIX "$state_file")"
fi
if [[ "$fingerprint" == "$last_fingerprint" && "$last_sent" =~ ^[0-9]+$ && $((now - last_sent)) -lt "$repeat_after_seconds" ]]; then
  echo "Unchanged alert suppressed until the repeat interval expires."
  exit 0
fi

message=$'⚠️ AssetGuard production requires attention\n'
message+="$(printf '%s\n' "${problems[@]}")"
message+="Checked: $(date --iso-8601=minutes)"
curl --fail --silent --show-error --max-time 20 \
  -X POST "https://api.telegram.org/bot${telegram_token}/sendMessage" \
  --data-urlencode "chat_id=${telegram_chat_id}" \
  --data-urlencode "text=${message}" >/dev/null

install -d -m 700 "$state_dir"
umask 077
printf 'FINGERPRINT=%s\nLAST_SENT_UNIX=%s\n' "$fingerprint" "$now" >"$state_file"
echo "Telegram accepted an alert for ${#problems[@]} problem(s)."
