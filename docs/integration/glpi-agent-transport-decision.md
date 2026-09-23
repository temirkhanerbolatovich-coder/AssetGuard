# GLPI Agent transport decision for MVP

## Decision

MVP supports the observed native GLPI Agent 1.19 XML transport as the primary path. The explicit bridge `scripts/windows/send-minimal-inventory.ps1` remains a deterministic fallback and fixture tool.

1. Agent sends XML `PROLOG` to `POST /glpi-agent` using HTTP Basic authentication.
2. AssetGuard returns XML `<RESPONSE>SEND</RESPONSE>`.
3. Agent sends XML `INVENTORY`; `DirectGlpiAgentAdapter` preserves the original XML in immutable evidence and maps sections to the canonical envelope.
4. The backend performs normalization, baseline comparison and incident creation.

## Why this boundary

The contract was observed on an installed upstream GLPI Agent 1.19 without modifying its code. A loopback probe received two `application/xml` POST requests at the configured URL: a 169-byte `PROLOG`, followed after `SEND` by a 14,339-byte `INVENTORY`. A second end-to-end run against the real FastAPI endpoint produced one immutable `PROCESSED` inventory and one `ONLINE` endpoint in a disposable PostgreSQL database.

The native endpoint accepts uncompressed XML only, enforces the common payload limit and rejects DTD/entity declarations. User is fixed to `assetguard`; password uses the primary/previous inventory shared secret. HTTP is allowed only for loopback lab verification; production uses HTTPS and a protected agent configuration. The bridge remains available for environments that do not enable managed `--server` mode.

## Compatibility boundary

The implementation intentionally covers the observed GLPI Agent 1.19 legacy XML inventory flow only. Compression, CONTACT/native JSON task planning, deployment/network-discovery tasks and universal version compatibility are not claimed. New agent versions require a contract test before changing the version lock.
