# AssetGuard — UI simplification publication and production acceptance

Date: 2026-10-06. Application commit:
`f4f56e7816035e01703305808dd0862a37de402e`, branch `main`.

## GitHub

- Commit `f4f56e7` pushed to GitHub `main`.
- [Push CI 37433147495](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37433147495): success.
- CI jobs: application tests and secret scan succeeded; scheduled/manual real
  Vision smoke was correctly skipped for a normal push.
- Local final acceptance before publication: 124 backend + 21 browser E2E,
  **145 passed**; JavaScript syntax and diff checks passed.

## Backup and rollback preparation

- Fresh encrypted R2 object:
  `assetguard-production-20261006-075950.sql.agbackup`.
- Isolated restore: PASS at `0026_telegram_notifications`, assets=220,
  endpoints=11.
- Previous API image retained as
  `assetguard-api:rollback-pref4f56e7-20261006`.
- Candidate `assetguard-api:candidate-f4f56e7` passed `pip check`.

## Production acceptance

- Accepted at `2026-10-06T08:21:52+00:00` on
  `https://assetguard-temirkhan.duckdns.org`.
- API image:
  `sha256:29062bad2c906e1b80afea322d20ee0ef3fb10a1778a0cdf7b60e9a6082a1fd3`.
- Only `containers-api-1` was recreated. PostgreSQL and Caddy retained their
  existing containers and volumes.
- `/health` and `/health/ready`: HTTP 200, `ok` and `ready`.
- Alembic: `0026_telegram_notifications (head)`.
- Public frontend bytes matched the exact Linux Git checkout:

| File | SHA-256 |
| --- | --- |
| `index.html` | `dbecddfa408e51da98629b6a617adba8246c1c3a42235ea08891be34e15a381b` |
| `app.js` | `dae84b5b51c43dd7831a50cdccff83abe75f0af86bc5bc1c875c0c103301574c` |
| `styles.css` | `b2b84e9e9f6187bbc245ffbfbb87926f57934613a7ecf68dbd0d3d30cacd95c4` |

- Public HTML contained the new administration task labels.
- Unauthenticated `/admin/endpoints`: 401.
- Browser `GET /glpi-agent`: expected 404; unauthenticated XML POST: 401.
- `assetguard-monitor.service` and `assetguard-notifications.service`: success.
- Monitor and notification timers: active; systemd failed units: none.

## Hosting clarification

The active public production is the established Oracle Cloud VM running the
repository Docker Compose stack. The project has no `render.yaml`, configured
Render service, Render CLI session or Render deployment. A duplicate Render
environment was not created because that would split production state and
credentials without an architecture decision.

## Remaining limitations

- Production Vision remains unavailable on the 1 GB Oracle profile.
- Manual NVDA/VoiceOver, Firefox/Safari, zoom 400% and moderated school-staff
  usability checks remain open.
- Agent 0.1.8 still needs a signed release and 3–5 PC fleet acceptance.
