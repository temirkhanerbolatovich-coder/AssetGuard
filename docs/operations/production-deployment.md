# Production deployment and recovery

## HTTPS deployment

`infra/containers/docker-compose.production.yml` runs PostgreSQL on a private Docker network, the AssetGuard API, and Caddy as the only public entry point. Set `ASSETGUARD_PUBLIC_HOST` to a DNS name pointing at the host, populate all secrets in `.env`, and run:

```powershell
docker compose --env-file .env -f infra/containers/docker-compose.production.yml up -d --build
```

Caddy obtains and renews the public certificate, redirects HTTP to HTTPS and adds HSTS. The API and PostgreSQL ports are not published. For an internal CA, replace the Caddy issuer according to the organisation PKI; agents must trust that CA and must not use `NO_SSL_CHECK`.

## Vision runtime and storage

The API image installs the optional `vision` dependencies. Uploaded and annotated images are stored in the persistent `assetguard-vision-data` volume; downloaded Hugging Face model files use `assetguard-model-cache`, so container recreation does not download the weights again. The first scan still initializes the model and may take longer, especially on CPU.

Configure `ASSETGUARD_VISION_MODEL_ID`, `ASSETGUARD_VISION_CONFIDENCE_THRESHOLD`, `ASSETGUARD_VISION_CLASSES` and `ASSETGUARD_VISION_MAX_IMAGE_BYTES` when defaults are unsuitable. The supplied Compose configuration is CPU-compatible. GPU passthrough, external object storage, image retention and camera ingestion require a separate deployment decision.

## Access and secret rotation

- The bootstrap admin key can create named `ADMIN` and `VIEWER` users through `POST /admin/users`.
- `POST /auth/login` returns a revocable 12-hour session token. The same token can be entered in the dashboard token field.
- Viewer sessions can read data but cannot change assets, baselines or incidents.
- During key rotation, put the old value in `ASSETGUARD_PREVIOUS_ADMIN_SHARED_SECRET` or `ASSETGUARD_PREVIOUS_INVENTORY_SHARED_SECRET`, deploy the new primary key, update clients, then remove the previous key and restart.

## Rate limiting and logging

The API applies `ASSETGUARD_RATE_LIMIT_PER_MINUTE` per client and boundary and emits request/status/duration records without tokens or payloads. Caddy should retain its own outer rate/connection limits when exposed to an untrusted network. Application and proxy logs must be access-controlled and retained according to organisation policy.

## Last-seen policy

`POST /admin/maintenance/evaluate-endpoints` marks endpoints older than `ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS` as `REQUIRES_VERIFICATION` and adds an audit entry. It never labels a device stolen or missing. The local scheduled inventory invokes this policy after collection; production should call it from the platform scheduler.

## Retention and backup

RawInventory and audit history are retained indefinitely in v0.1 because they are immutable evidence. Shorter retention requires a separately approved archive/export migration; direct deletion is blocked by database triggers.

Vision images are operational artifacts rather than immutable hardware evidence. The demo keeps them in a named volume without automatic deletion; define an organisation retention policy before collecting real room photographs.

Create an SQL backup:

```powershell
pwsh -File scripts/windows/backup-database.ps1
```

Backups are written under `.local/backups`, outside Git. Copy them to encrypted storage and test restoration periodically. Restore requires explicit PowerShell confirmation:

```powershell
pwsh -File scripts/windows/restore-database.ps1 -BackupFile .local/backups/<file>.sql
```

Stop API writes before a restore. After restoration, run migrations, verify `/health`, compare entity counts and perform one read-only dashboard check.
