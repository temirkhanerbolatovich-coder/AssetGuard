# Production deployment and recovery

> **Сверено 2026-10-07.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

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
- Viewer-level routes admit ADMIN, VIEWER, LOCATION_MANAGER and INVENTORY_CLERK. Resource reads require tenant/location scope; asset/inspection/physical decisions require ADMIN or EDITOR grant. Hardware baseline and technical incident decisions remain ADMIN-only. Role name alone does not grant write access.
- During key rotation, put the old value in `ASSETGUARD_PREVIOUS_ADMIN_SHARED_SECRET` or `ASSETGUARD_PREVIOUS_INVENTORY_SHARED_SECRET`, deploy the new primary key, update clients, then remove the previous key and restart.

## Current production checkpoint

Rechecked 2026-10-06 19:07:22 UTC: accepted application `7c45435`, image `sha256:1a98957a3ef6829a3281d32c5e9130157a4e73feff730e2e4a165da7902beda1`, Alembic `0026`; public/frontend/API freshness and supported-version checks passed. Fresh R2 object `assetguard-production-20261006-183238.sql.agbackup` restored in isolation: assets=220, endpoints=11. PostgreSQL and Caddy containers/volumes were preserved; monitor/notifications timers resumed. [Release evidence](../../outputs/assetguard-agent-status-publication-2026-10-07.md). Documentation acceptance can advance checkout HEAD without changing application image; the dated records below remain historical.

## Native GLPI Agent target

For legacy native daemons, configure a supported upstream GLPI Agent 1.19 or 1.20 server target as `https://<ASSETGUARD_PUBLIC_HOST>/glpi-agent`, HTTP Basic user issued for that device, and its one-time inventory secret. New installer deployments are pinned to 1.20. Apply the repository minimal privacy profile and `no-compression = 1`; do not put credentials in source control or a world-readable script. The agent must trust the Caddy/public or organisation CA. Validate one `PROLOG` and one `INVENTORY` in logs, then confirm a single `PROCESSED` inventory and `ONLINE` endpoint through the admin API.

Installer 0.1.8 uses local hardware collection plus a SYSTEM delivery task and protected durable FIFO. It disables the native daemon and reuses `/glpi-agent` authentication; configure only one uploader per PC. [Install/update/ACK/quota contract](../features/agent-continuous-inventory.md). Do not infer fleet acceptance from successful ingestion on one PC.

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

The Agent 0.1.6 pilot release was deployed later on 2026-09-27 from application
commit `7a3f7f2`. It pins clean WinGet installations to GLPI Agent 1.20, keeps
1.19 compatible, rejects unknown versions and exposes the reported Agent version
in the device card. No database migration was required. Post-deployment readiness,
Alembic head, public `app.js` hash and server monitoring passed; the previous API
image remains tagged as `assetguard-api:rollback-8434dfb`.

## Historical pre-rollout note: repository changes awaiting deployment

Repository commit `3216a11` advances Alembic head to `0025_agent_reenrolment` and adds installer `0.1.7` source with lifecycle version reporting and administrator-approved re-enrolment. Local backend, browser E2E and installer compilation passed, but this revision is not recorded as deployed by this runbook. Before rollout:

1. create and verify a fresh encrypted backup;
2. retain the current API image under an explicit rollback tag;
3. deploy the exact commit and apply migration `0025`;
4. verify readiness, public asset hashes and re-enrolment admin routes;
5. test `0.1.7` on the third pilot PC before publishing its GitHub release.

Do not rewrite the earlier deployment record: it is evidence of the exact state that was verified on 2026-09-27.

## Deployment record: 2026-10-04

Application commit `93ff8ed704635c26571d7866766e010eb42e29c6` was pushed to `main` and accepted on production at **18:28:53 UTC**. Both [push CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223402190) and [manual CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223446315) succeeded: 80 backend tests, 2 browser E2E, dependency audit, secret scan and manual real-model download/inference (23 detections). A transient GitHub API rate limit in the manual secret-scan first attempt resolved on retry without bypassing the check.

Before deployment, a fresh R2 object `assetguard-production-20261004-181323.sql.agbackup` restored into isolated PostgreSQL 17 at `0024`, with 216 assets and 11 endpoints. A second isolated rehearsal applied `0025` and compared every pre-existing application table's count and row fingerprint; all were unchanged. It then downgraded to `0024`, started the previous API image normally and checked readiness, re-upgraded to `0025`, and started the candidate with authenticated assets/operations/re-enrolment reads. Production was never connected to this rehearsal.

The server checkout advanced from `1e82e75` to the exact application commit. The Oracle Free image excludes optional ML dependencies as before. The previous image remains tagged `assetguard-api:rollback-pre93ff8ed-20261004`; the accepted candidate remains `assetguard-api:candidate-93ff8ed`. Only the API was recreated:

```bash
docker compose --env-file .env \
  -f infra/containers/docker-compose.production.yml \
  -f infra/containers/docker-compose.oracle-free.yml \
  up -d --no-deps --no-build api
```

PostgreSQL and Caddy container IDs stayed unchanged. `/health` and `/health/ready`, all public frontend hashes, actual Alembic `0025`, 60 public OpenAPI admin operations and authenticated/unauthenticated access checks passed. The monitor was updated with a byte comparison; its previous script and private configuration were preserved. One authorized real Telegram test alert was accepted, and the repeat was suppressed using a separate state directory. The five-minute timer resumed active; systemd reported no failed units. Operations showed 1 online and 10 stale endpoints with zero failed ingest/conflicts; real PC acceptance remains pending.

A fresh post-deployment R2 object `assetguard-production-20261004-182927.sql.agbackup` was restored separately at **18:30:15 UTC**: `0025_agent_reenrolment`, assets=216, endpoints=11, PASS. Both backup/restore services returned `Result=success` and `ExecMainStatus=0`. Daily/weekly automatic server jobs earlier on 2026-10-04 also passed. PostgreSQL backups still exclude the Vision image volume. Exact hashes, counts and limits are recorded in [release acceptance](../../outputs/assetguard-release-2026-10-04.md).

### Recovery for the 0025 release

The previous image runs `alembic upgrade head` before Uvicorn. Its migrations do not know `0025`, so changing the image tag alone is insufficient. The tested sequence was candidate migration downgrade on an isolated pre-release copy, followed by the ordinary previous-image startup; it was **not** a production rollback or full failover test.

Downgrade `0025` deletes the re-enrolment table and detaches revoked credential bindings before restoring the previous uniqueness constraint. The rehearsed copy had no re-enrolment requests and no bound revoked credentials. Before any later rollback, stop writes, take a fresh backup, inspect requests and credential history added since deployment, and choose between retaining the current schema with a compatible application or a reviewed downgrade/restore plan that accounts for those writes. Do not blindly run downgrade or restore against a live database. Retain the rollback image and pre/post-deployment R2 objects until the recovery window has closed.

Documentation can advance Git checkout HEAD after acceptance without rebuilding the image. At the 2026-10-04 checkpoint the verified application was `93ff8ed` and installer `0.1.7` was unsigned, unpublished and pending real-PC acceptance. The 2026-10-06 checkpoint below supersedes those versions; the earlier record remains evidence of its original date.

## Deployment record: 2026-10-06 UI simplification

Application commit `f4f56e7816035e01703305808dd0862a37de402e` was pushed to
`main` and accepted on production at **08:21:52 UTC**. [Push CI
37433147495](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37433147495)
completed successfully, including backend/browser tests, dependency audit,
secret scan and static checks.

Before the switch, the server created the encrypted R2 object
`assetguard-production-20261006-075950.sql.agbackup`. Its isolated restore
passed at revision `0026_telegram_notifications` with 220 assets and 11
endpoints. The previous API image is retained as
`assetguard-api:rollback-pref4f56e7-20261006`; the accepted image is retained as
`assetguard-api:candidate-f4f56e7` with image id
`sha256:29062bad2c906e1b80afea322d20ee0ef3fb10a1778a0cdf7b60e9a6082a1fd3`.
Only the API container was recreated. PostgreSQL and Caddy containers retained
their original creation times and persistent data.

Post-deployment `/health` and `/health/ready` returned HTTP 200; Alembic stayed
at `0026`. Public `index.html`, `app.js` and `styles.css` matched the exact
Linux Git checkout. Unauthenticated admin access returned 401, browser GET to
the machine endpoint returned the expected 404, and unauthenticated GLPI POST
returned 401. Monitor and Telegram delivery services completed successfully,
both timers resumed active, and systemd reported no failed units. Exact hashes
and the scope of verification are recorded in [the release
report](../../outputs/assetguard-ui-release-2026-10-06.md).

The public host remains the established Oracle Cloud Docker Compose deployment.
There is no Render Blueprint or Render service in this repository; no second
production environment was created merely to satisfy an incorrect provider
label.
