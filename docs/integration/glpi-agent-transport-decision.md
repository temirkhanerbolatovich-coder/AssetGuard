# GLPI Agent transport decision for MVP

## Decision

MVP uses autonomous local GLPI collection plus the explicit AssetGuard bridge `scripts/windows/send-minimal-inventory.ps1`.

1. `collect-minimal-inventory.ps1` produces a privacy-limited JSON locally.
2. `send-minimal-inventory.ps1` reads that exact file and posts it to `POST /internal/inventories` with the AssetGuard ingest token and an idempotency key.
3. The backend performs raw-evidence storage, normalization, baseline comparison and incident creation.

## Why this boundary

GLPI Agent's managed `--server` mode includes server-controlled task planning and a GLPI-specific protocol. AssetGuard does not pretend to implement that protocol. The autonomous mode keeps collection scope and transport under AssetGuard control, and lets the gateway use its own authenticated contract.

The bridge accepts HTTPS endpoints. HTTP is allowed only for `localhost`/`127.0.0.1` lab verification. The ingest token is supplied from `ASSETGUARD_INVENTORY_SHARED_SECRET` or an explicit process argument; it is not written to configuration or source control.

## Deferred compatibility spike

Native GLPI server protocol compatibility is explicitly out of MVP scope. It requires a separate compatible-server test matrix (prolog/control response, compression and JSON/XML negotiation), and must not be inferred from a successful custom JSON ingest.
