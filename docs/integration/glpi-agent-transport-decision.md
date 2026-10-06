# GLPI Agent transport decision for MVP

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

## Decision

MVP supports the observed native GLPI Agent 1.19 and 1.20 XML transport as the primary path. The explicit bridge `scripts/windows/send-minimal-inventory.ps1` remains a deterministic fallback and fixture tool.

1. Agent sends XML `PROLOG` to `POST /glpi-agent` using HTTP Basic authentication.
2. AssetGuard returns XML `<RESPONSE>SEND</RESPONSE>`.
3. Agent sends XML `INVENTORY`; `DirectGlpiAgentAdapter` preserves the original XML in immutable evidence and maps sections to the canonical envelope.
4. The backend performs normalization, baseline comparison and incident creation.

## Why this boundary

The contract was first observed on an installed upstream GLPI Agent 1.19 without modifying its code. A loopback probe received two `application/xml` POST requests at the configured URL: a 169-byte `PROLOG`, followed after `SEND` by a 14,339-byte `INVENTORY`. A second end-to-end run against the real FastAPI endpoint produced one immutable `PROCESSED` inventory and one `ONLINE` endpoint in a disposable PostgreSQL database. GLPI Agent 1.20 later completed the same authenticated production flow from a second real Windows-PC; the version value is preserved in RawInventory and shown in the device card.

The native endpoint accepts uncompressed XML only, enforces the common payload limit and rejects DTD/entity declarations. The primary path uses a per-device HTTP Basic username and secret, stored as a password hash on the server. User `assetguard` with the primary/previous shared secret remains a legacy migration fallback. HTTP is allowed only for loopback lab verification; production uses HTTPS and a protected agent configuration. The bridge remains available for environments that do not enable managed `--server` mode.

Installer 0.1.8 instead runs the same upstream collector locally, persists XML in a bounded FIFO and uploads INVENTORY with the existing Basic credential. Its collection does not depend on a successful PROLOG/network round trip. Legacy native daemons use the observed PROLOG flow above and receive the configured interval (360 seconds by default). [Current contract](../features/agent-continuous-inventory.md), [ADR-008](../decisions/ADR-008-agent-durable-delivery.md).

## Compatibility boundary

The implementation intentionally covers the observed GLPI Agent 1.19/1.20 legacy XML inventory flow only. Compression, CONTACT/native JSON task planning, deployment/network-discovery tasks and universal version compatibility are not claimed. New agent versions require a contract test before changing the version lock.
