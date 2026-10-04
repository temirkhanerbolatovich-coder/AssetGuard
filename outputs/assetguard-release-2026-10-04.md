# AssetGuard — publication and production acceptance, 2026-10-04

Application commit: `93ff8ed704635c26571d7866766e010eb42e29c6`, `main`.

This record continues the [local stabilization report](assetguard-stage-1-2026-10-04.md). The original specification and Vision detector/model were not changed by this release.

## Publication and CI

- Commit `93ff8ed` pushed to GitHub `main`.
- [Push CI 37223402190](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223402190): success, application tests and full-history secret scan.
- [Manual CI 37223446315](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223446315): success, including real Grounding DINO download/inference, **23 detections**.
- Actual CI output: **80 backend tests**, **2 browser E2E**, strict dependency audit without known vulnerabilities; JavaScript, PowerShell, Linux and Compose checks passed.
- The manual secret-scan first attempt failed because an unauthenticated GitHub API rate limit caused the action to require a license. Its retry succeeded on the same application commit; no scan bypass or license workaround was introduced. Push scan also succeeded.

## Pre-deployment backup and rehearsal

- SSH read confirmed the old server checkout at `1e82e75`, runtime schema `0024_physical_asset_operations`, and clean Git state.
- Fresh encrypted R2 object: `assetguard-production-20261004-181323.sql.agbackup`.
- Backup and isolated off-site restore services: `Result=success`, `ExecMainStatus=0`.
- Restored data: **216 assets, 11 endpoints, 12 active credentials**; no revoked credential was bound to an endpoint.
- Previous API image retained as `assetguard-api:rollback-pre93ff8ed-20261004`.
- Oracle Free API image built from exact application commit `93ff8ed`, with optional ML dependencies excluded as before.
- Separate PostgreSQL 17 container had no published ports and contained only the restored copy. Upgrade `0024 → 0025` preserved counts and row fingerprints of **all pre-existing application tables**, including raw evidence and audit.
- Downgrade to `0024` preserved all other tables, and the previous API image started with its ordinary migration/start command; readiness returned HTTP 200.
- Re-upgrade to `0025` and candidate startup passed: readiness, authenticated operations/assets/re-enrolment reads and the re-enrolment OpenAPI route.
- The first one-off harness used a misspelled re-enrolment URL and ended with HTTP 404; the corrected complete rehearsal passed. The production database was never used by either rehearsal.

## Production acceptance

- Deployment accepted **2026-10-04 18:28:53 UTC** at `https://assetguard-temirkhan.duckdns.org`.
- API runtime image: `sha256:11493e8a23d2cab5cc3a9f783d3cdaebede83e2dbc5c401687784651e414fca7`; retained candidate tag `assetguard-api:candidate-93ff8ed`.
- Only API was recreated via the production + Oracle Free Compose configuration, `up -d --no-deps --no-build api`. PostgreSQL and Caddy container IDs stayed unchanged; existing volumes were retained.
- Production image `pip check`: no broken requirements.
- Public `/health` and `/health/ready`: HTTP 200, `ok`/`ready`.
- All public frontend hashes matched the deployed image:

| File | SHA-256 |
| --- | --- |
| index.html | `fff189465409432dddddae4df9bb71f7c4bdfdf61b1ab315522e3f9b4e261b40` |
| app.js | `b5426826f3d03eba97c91f5fbd81d4a7eb2c9af207a61b11514f696895810479` |
| styles.css | `0ddbe3f5a0da478f444e00f3d56f29e71bd25708801dd39f4ae3c7fe23cffe17` |

- Public OpenAPI: **60 admin operations**, including re-enrolment routes.
- Assets, Agent credentials and re-enrolment reads: authenticated HTTP 200; unauthenticated public reads HTTP 401.
- Actual schema `0025_agent_reenrolment`; **216 assets, 11 endpoints, 51 raw inventories, 51 hardware snapshots, 17 credentials, 0 re-enrolment requests**. No production domain data was edited merely for acceptance.
- Operations: **1 online, 10 stale, 0 offline, 0 identity conflicts, 0 failed ingests**. The latest inventory timestamp was `2026-10-04T11:32:21.987203+00:00`. Stale endpoints require real PC/fleet follow-up; they are not an API outage.
- Installed monitor bytes matched repository source. Previous installed monitor retained as `/usr/local/lib/assetguard-server-monitor.pre93ff8ed.sh`; existing private configuration preserved.
- With explicit user authorization, one actual Telegram test alert was accepted (`ok=true` plus `message_id` required by the script); immediate repeat printed `Unchanged alert suppressed until the repeat interval expires.` The separate state directory `/var/lib/assetguard-monitor-release-93ff8ed` preserved normal monitor state. Its two conditions were TEST ONLY and the actual 10 stale endpoints.
- Monitor timer resumed active. Systemd had no failed units; available RAM after rollout was about **332 MB**, no swap, Oracle Free limits retained. Production Vision remains unavailable in this profile.
- Fresh **post-deployment** encrypted R2 backup: `assetguard-production-20261004-182927.sql.agbackup`. Backup service and off-site restore both returned `Result=success`, `ExecMainStatus=0`; restored schema **0025**, **216 assets / 11 endpoints**, PASS at **18:30:15 UTC**. Both R2 uploads encountered a transient HTTP 501 on their first attempt and succeeded on retry; no unresolved job failure remained.
- Earlier automatic daily backup at 02:00 UTC and weekly restore at 03:00 UTC on 2026-10-04 also completed successfully. Windows scheduled jobs were not re-run in this deployment stage.

The final documentation commit records this acceptance and can advance checkout HEAD without rebuilding the frozen application image. Runtime application code remains `93ff8ed`; documentation HEAD and runtime image are distinct release facts.

## Recovery limits and next work

The tested downgrade used a pre-release copy with no re-enrolment requests and no bound revoked credentials. Migration `0025` downgrade deletes re-enrolment requests and detaches revoked credential bindings before restoring the old unique constraint. The old image's normal startup cannot interpret revision `0025`; changing only the image tag is insufficient. Before a later production rollback, stop writes, inspect new re-enrolment/history data, preserve a fresh backup and select a recovery plan that accounts for writes since this release. No production downgrade or restore was performed.

Windows installer `0.1.7` remains an unsigned, unpublished pilot candidate. Fleet acceptance on 3–5 real PCs, school data governance, signing/update rollback and production Vision infrastructure remain separate gates. PostgreSQL backup excludes the Vision image volume.
