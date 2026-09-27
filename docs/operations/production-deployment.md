# Production deployment and recovery

## HTTPS deployment

`infra/containers/docker-compose.production.yml` runs PostgreSQL on a private Docker network, the AssetGuard API, and Caddy as the only public entry point. Set `ASSETGUARD_PUBLIC_HOST` to a DNS name pointing at the host, populate all secrets in `.env`, and run:

```powershell
docker compose --env-file .env -f infra/containers/docker-compose.production.yml up -d --build
```

Caddy obtains and renews the public certificate, redirects HTTP to HTTPS and adds HSTS. The API and PostgreSQL ports are not published. For an internal CA, replace the Caddy issuer according to the organisation PKI; agents must trust that CA and must not use `NO_SSL_CHECK`.

## Vision runtime and storage

The API image installs the optional `vision` dependencies. Uploaded and annotated images are stored in the persistent `assetguard-vision-data` volume; downloaded Hugging Face model files use `assetguard-model-cache`, so container recreation does not download the weights again. The first scan still initializes the model and may take longer, especially on CPU.

### Oracle Always Free (1 GB RAM)

The free `VM.Standard.E2.1.Micro` server is sufficient for the inventory API,
school hierarchy, RBAC, PDF/Excel import/export, the dashboard and Windows
Agent ingestion. It is not suitable for the PyTorch Vision runtime. Deploy it
with the memory-safe overlay:

```powershell
docker compose --env-file .env `
  -f infra/containers/docker-compose.production.yml `
  -f infra/containers/docker-compose.oracle-free.yml up -d --build
```

This image does not install `torch` or `transformers`; opening a Vision scan
will clearly report that its runtime is unavailable. For a real Vision pilot,
move the same production compose configuration to a host with at least 4 GB
RAM, omit the Oracle overlay and redeploy. All existing inventory data stays in
the PostgreSQL volume.

Configure `ASSETGUARD_VISION_MODEL_ID`, `ASSETGUARD_VISION_CONFIDENCE_THRESHOLD`, `ASSETGUARD_VISION_CLASSES` and `ASSETGUARD_VISION_MAX_IMAGE_BYTES` when defaults are unsuitable. The supplied Compose configuration is CPU-compatible. GPU passthrough, external object storage, image retention and camera ingestion require a separate deployment decision.

## Access and secret rotation

- The bootstrap admin key can create named `ADMIN`, `VIEWER`, `LOCATION_MANAGER` and `INVENTORY_CLERK` users through `POST /admin/users`; assign a school/area grant before expecting a scoped user to see assets.
- `POST /auth/login` returns a revocable 12-hour session token. The same token can be entered in the dashboard token field.
- Viewer sessions can read data but cannot change assets, baselines or incidents.
- During key rotation, put the old value in `ASSETGUARD_PREVIOUS_ADMIN_SHARED_SECRET` or `ASSETGUARD_PREVIOUS_INVENTORY_SHARED_SECRET`, deploy the new primary key, update clients, then remove the previous key and restart.

## Native GLPI Agent target

Configure a supported upstream GLPI Agent 1.19 or 1.20 server target as `https://<ASSETGUARD_PUBLIC_HOST>/glpi-agent`, HTTP Basic user issued for that device, and its one-time inventory secret. New installer deployments are pinned to 1.20. Apply the repository minimal privacy profile and `no-compression = 1`; do not put credentials in source control or a world-readable script. The agent must trust the Caddy/public or organisation CA. Validate one `PROLOG` and one `INVENTORY` in logs, then confirm a single `PROCESSED` inventory and `ONLINE` endpoint through the admin API.

## Rate limiting and logging

The API applies `ASSETGUARD_RATE_LIMIT_PER_MINUTE` per client and boundary and emits request/status/duration records without tokens or payloads. Caddy should retain its own outer rate/connection limits when exposed to an untrusted network. Application and proxy logs must be access-controlled and retained according to organisation policy.

## Last-seen policy

`POST /admin/maintenance/evaluate-endpoints` marks endpoints older than `ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS` as `REQUIRES_VERIFICATION` and adds an audit entry. It never labels a device stolen or missing. The local scheduled inventory invokes this policy after collection; production should call it from the platform scheduler.

## Retention and backup

RawInventory and audit history are retained indefinitely in v0.1 because they are immutable evidence. Shorter retention requires a separately approved archive/export migration; direct deletion is blocked by database triggers.

Vision images are operational artifacts rather than immutable hardware evidence. The demo keeps them in a named volume without automatic deletion; define an organisation retention policy before collecting real room photographs.

Create an AES-256-GCM encrypted SQL backup. The script prompts for a passphrase unless `ASSETGUARD_BACKUP_PASSPHRASE` is present in the process environment:

```powershell
pwsh -File scripts/windows/backup-database.ps1
```

Backups are written as `.sql.agbackup` under `.local/backups`, outside Git. `-OffsiteTarget` can copy the encrypted file to an external directory or an already configured `rclone` remote. Test restoration periodically. Restore requires the passphrase and explicit PowerShell confirmation:

```powershell
pwsh -File scripts/windows/restore-database.ps1 -BackupFile .local/backups/<file>.sql.agbackup
```

Stop API writes before a restore. After restoration, run migrations, verify `/health`, compare entity counts and perform one read-only dashboard check.

For a non-destructive restore rehearsal use the isolated verifier instead. It decrypts only to a temporary file, restores to a disposable PostgreSQL container with no published ports, checks the Alembic revision and key entity counts, then destroys the container and temporary SQL. For a backup created immediately beforehand, compare its read-only counts with the source database:

```powershell
pwsh -File scripts/windows/verify-backup-restore.ps1 `
  -BackupFile .local/backups/<file>.sql.agbackup `
  -CompareWithCurrentDatabase
```

Never use `restore-database.ps1` merely to prove that a backup works: that command writes into the operational database.

For the configured Cloudflare R2 remote, create and rehearse an off-site copy without writing to the operational database:

```powershell
pwsh -File scripts/windows/backup-database.ps1 `
  -OffsiteTarget 'assetguard-r2:assetguard-backups/daily' `
  -NonInteractive

pwsh -File scripts/windows/invoke-latest-backup-rehearsal.ps1 `
  -OffsiteTarget 'assetguard-r2:assetguard-backups/daily'
```

The R2 token must be an account token with Object Read & Write limited to the backup bucket. Do not store its Access Key ID or Secret Access Key in the repository or runbook. On 2026-09-27 the Windows flow uploaded `assetguard-20260927-150843.sql.agbackup`, restored it into an isolated PostgreSQL container and returned `PASS`; the daily and weekly Task Scheduler jobs returned `LastTaskResult=0`. The permanent server then uploaded `assetguard-production-20260927-105228.sql.agbackup` and completed its isolated rehearsal with revision `0024_physical_asset_operations`, `assets=211` and `endpoints=1`. The daily backup, weekly rehearsal and five-minute monitor timers were active; backup, rehearsal and monitor services all returned `Result=success`. At verification time R2 contained two valid production objects and none older than 30 days. PostgreSQL backups do not include the Vision image volume.

Use the monitor's explicit test mode to verify Telegram delivery without stopping production:

```bash
sudo /usr/local/lib/assetguard-server-monitor.sh \
  --project-dir /opt/assetguard \
  --config /etc/assetguard/server-monitor.env \
  --test-alert
```

The message is marked `TEST ONLY` and states that production remains online. Repeating the same command inside four hours must print `Unchanged alert suppressed until the repeat interval expires.` instead of sending another message. An unchanged real incident is sent again after four hours. On 2026-09-27 Telegram accepted the first controlled alert, the immediate second run was deduplicated, and a normal run printed `AssetGuard production checks passed.`

## Deployment record: 2026-09-27

Production at `https://assetguard-temirkhan.duckdns.org/` was updated from
`ad904da` to `8434dfb`. Before the rollout, the server created
`assetguard-production-20260927-114122.sql.agbackup` and restored it into an
isolated PostgreSQL instance at Alembic revision
`0024_physical_asset_operations` with `assets=211` and `endpoints=1`.

The Oracle Free overlay remained enabled, so Vision runtime dependencies were
not installed on the 1 GB host. The API image and Caddy container were replaced;
the PostgreSQL container and persistent volume were left running. The previous
API image was retained locally as `assetguard-api:rollback-ad904da`.

Post-deployment verification confirmed:

- `/health/ready` returned `status=ready`;
- Alembic reported `0024_physical_asset_operations (head)`;
- the public `index.html`, `app.js` and `styles.css` hashes matched the files in
  the deployed API image;
- the new sidebar dashboard rendered from the public HTTPS endpoint;
- `assetguard-monitor.service` returned `Result=success`; and
- systemd reported no failed units.
