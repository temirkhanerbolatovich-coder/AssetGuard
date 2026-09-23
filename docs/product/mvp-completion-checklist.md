# AssetGuard MVP v0.1 — чек-лист завершения

Дата актуализации: 2026-09-23. Чек-лист включает исходный computer inventory MVP и демонстрационный AssetGuard Vision vertical slice.

## Текущая оценка

- Демонстрационный MVP через native GLPI transport и explicit bridge: **готов**.
- Native GLPI Agent 1.19 `PROLOG → INVENTORY` проверен реальным loopback end-to-end; production TLS/DNS acceptance остаётся отдельным шагом.
- Production hardening foundation реализован в коде; публичное развёртывание и recovery rehearsal требуют целевого домена/хоста.

## Реализовано

| Область | Статус | Результат |
| --- | --- | --- |
| GLPI Agent | Готово | GLPI Agent 1.19 проверен на реальном Windows-PC; есть version lock и minimal privacy profile. |
| Collection/transport | Готово для 1.19 | Native uncompressed XML PROLOG/INVENTORY и explicit JSON bridge проверены end-to-end. |
| Raw evidence | Готово | Append-only JSONB payload, hash, idempotency и processing status. |
| PostgreSQL | Готово | Migrations для raw inventory, snapshots, baseline, change events, incidents, assets, users и Vision. |
| Asset / endpoint | Готово | Assets связаны с актуальным endpoint; один asset имеет только один текущий endpoint. |
| Snapshots | Готово | Нормализуются RAM, storage, CPU, GPU, motherboard, network и monitor observations. |
| Baseline | Готово | Принятие только явным действием; automatic baseline update отсутствует. |
| RAM/storage diff | Готово | Added/removed, completeness guard, deterministic deduplication. |
| Incidents/history | Готово | Create/classify/resolve incident и append-only audit history. |
| PARTIAL safety | Готово | Partial inventory не создаёт ложное удаление RAM/SSD. |
| Dashboard | Готово | Assets/endpoints, last seen/status, linking, baseline/current hardware, evidence, incidents и timeline. |
| AssetGuard Vision | Готово для demo | Image upload, Grounding DINO, bounding boxes, counts, explicit room baseline, comparison, `WARNING` и history. |
| Background demo | Готово | User-level demo tasks и production Compose deployment с restart policy. |
| Local package | Готово | ZIP без secret/database/log data, startup scripts и documentation. |
| GitHub | Готово | Public repository: `temirkhanerbolatovich-coder/AssetGuard`. |
| Automated tests | Готово | Disposable PostgreSQL, JSON/native inventory, Vision E2E, auth lifecycle и identity conflict; 14 tests + GitHub Actions workflow. |

## Оставшаяся работа

### P0 — demo MVP

- [x] Admin API: endpoint list/detail, snapshot list/detail, raw inventory list/detail, Asset update.
- [x] Dashboard: last seen, endpoint status, capacity presentation, evidence и читаемый timeline.
- [x] Identity: SMBIOS/BIOS/chassis/motherboard serial, MAC, agent ID и hostname history.
- [x] Identity conflicts: разные endpoint matches переводятся в `IDENTITY_CONFLICT`, ambiguous payload получает processing error.
- [x] Events: `HOSTNAME_CHANGED`, evidence-aware `COMPONENT_CHANGED` и `COMPONENT_REPLACED`.
- [x] Event: `DEVICE_IDENTITY_CHANGED` при смене strong identifier и сохранении другой стабильной identity.
- [x] Tests: disposable PostgreSQL и обязательные RAM/SSD/identical/PARTIAL/hostname/dedup fixtures.
- [x] Automated end-to-end: baseline → change → one incident → decision → new baseline → identical rescan.
- [x] Vision end-to-end: upload → detections/counts → annotated image → baseline → repeat scan → `WARNING` → history.

### P1 — production hardening foundation

- [x] HTTPS reverse proxy: production Compose + Caddy; certificate validation не отключается.
- [x] Named ADMIN/VIEWER users, revocable sessions, role checks и staged secret rotation.
- [x] Login/logout, session revoke, user disable/password rotation и authenticated audit actor.
- [x] Rate limiting, security headers, request logging, immutable evidence retention и backup/restore runbook.
- [x] Endpoint last-seen policy: `REQUIRES_VERIFICATION`, без автоматического вывода о пропаже или краже.
- [x] Managed production deployment: Docker restart policy, независимо от интерактивной Windows-сессии.
- [ ] Deployment acceptance на целевом сервере: DNS, публичный/корпоративный сертификат, encrypted off-host backup и restore rehearsal.
- [x] Native GLPI Agent 1.19 protocol spike и `DirectGlpiAgentAdapter`.
- [ ] Browser E2E и optional real Grounding DINO CI smoke job.

### За пределами текущего demo

- RTSP/camera scheduler, quality gate, multi-frame aggregation и `ANOMALY` confirmation;
- Institution/Building/Floor hierarchy, QR/mobile обход, 1C, Excel, AD, Linux/macOS;
- связывание Vision detection с конкретным endpoint/asset;
- custom agent, remote desktop, helpdesk, automatic theft detection.

## Критерий завершения первой части

Demo MVP считается завершённым, когда оператор может без ручной работы с БД выполнить два сценария через UI/API: (1) получить inventory устройства, связать его с Asset, принять baseline, показать hardware change и Incident с evidence; (2) загрузить фото помещения, увидеть bounding boxes/counts, сохранить Vision baseline и получить `WARNING` при расхождении повторного scan.
