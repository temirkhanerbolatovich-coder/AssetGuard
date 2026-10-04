#!/usr/bin/env bash
# Delivers committed incident notifications using existing root-only bot configuration.
set -euo pipefail
project_dir="/opt/assetguard"
config_file="/etc/assetguard/server-monitor.env"
enqueue_test=false
while [[ $# -gt 0 ]]; do
  case "$1" in
    --project-dir) project_dir="$2"; shift 2 ;;
    --config) config_file="$2"; shift 2 ;;
    --enqueue-test) enqueue_test=true; shift ;;
    *) echo "Unknown argument: $1" >&2; exit 2 ;;
  esac
done
[[ -r "$config_file" && -r "$project_dir/.env" ]]
host="$(sed -n 's/^ASSETGUARD_PUBLIC_HOST=//p' "$project_dir/.env" | tail -n 1 | sed 's/\r$//')"
[[ -n "$host" ]]
api="$(docker compose --env-file "$project_dir/.env" -f "$project_dir/infra/containers/docker-compose.production.yml" -f "$project_dir/infra/containers/docker-compose.oracle-free.yml" ps -q api)"
[[ -n "$api" ]] || { echo 'API container is unavailable; notifications remain queued.' >&2; exit 1; }
arguments=()
[[ "$enqueue_test" != true ]] || arguments+=(--enqueue-test)
docker exec --env-file "$config_file" --env "ASSETGUARD_PUBLIC_URL=https://$host" "$api" python -m assetguard.modules.notifications.delivery "${arguments[@]}"
