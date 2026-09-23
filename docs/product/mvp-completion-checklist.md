# AssetGuard MVP v0.1 — чек-лист завершения

Дата актуализации: 2026-09-23. Vision Inventory не входит в этот чек-лист и остаётся отдельным следующим этапом.

## Текущая оценка

- Демонстрационный MVP: **75–80%**.
- Production-ready система: **35–40%**.

## Реализовано

| Область | Статус | Результат |
| --- | --- | --- |
| GLPI Agent | Готово | GLPI Agent 1.19 проверен на реальном Windows-PC; есть version lock и minimal privacy profile. |
| Collection/transport | Готово | Локальный collection и explicit bridge в AssetGuard ingest API. |
| Raw evidence | Готово | Append-only JSONB payload, hash, idempotency и processing status. |
| PostgreSQL | Готово | Migrations для raw inventory, snapshots, baseline, change events, incidents, assets. |
| Asset / endpoint | Готово | Assets связаны с актуальным endpoint; один asset имеет только один текущий endpoint. |
| Snapshots | Готово | Нормализуются RAM, storage, CPU и GPU. |
| Baseline | Готово | Принятие только явным действием; automatic baseline update отсутствует. |
| RAM/storage diff | Готово | Added/removed, completeness guard, deterministic deduplication. |
| Incidents/history | Готово | Create/classify/resolve incident и append-only audit history. |
| PARTIAL safety | Готово | Partial inventory не создаёт ложное удаление RAM/SSD. |
| Dashboard | Частично | Assets, baseline/current hardware, CPU/GPU/RAM/storage, changes, incidents и history. |
| Background demo | Частично | User-level Scheduled Tasks: API при logon и privacy-limited inventory раз в 4 часа. |
| Local package | Готово | ZIP без secret/database/log data, startup scripts и documentation. |
| GitHub | Готово | Public repository: `temirkhanerbolatovich-coder/AssetGuard`. |
| Automated tests | Частично | 7 tests и sanitized fixtures; изолированный full E2E fixture database ещё не создан. |

## Оставшаяся работа

### P0 — закончить demo MVP

- [ ] Admin API: endpoint list/detail, snapshot list/detail, raw inventory list/detail, Asset update.
- [ ] Dashboard: last seen, endpoint status, capacity presentation, читаемый timeline и единый visual system.
- [ ] Identity: BIOS/chassis/motherboard serial, MAC, hostname history.
- [ ] Events: `HOSTNAME_CHANGED`; evidence-aware `COMPONENT_CHANGED` и `COMPONENT_REPLACED` при достаточных доказательствах.
- [ ] Tests: автоматизировать обязательные fixtures на отдельной PostgreSQL test database: RAM removal, SSD replacement, identical scan, PARTIAL software, hostname change, dedup/incident workflow.
- [ ] Провести end-to-end demo: baseline → hardware change → exactly one incident → decision → explicit new baseline → identical rescan without new events.

### P1 — production hardening

- [ ] HTTPS reverse proxy и нормальная certificate validation вне localhost.
- [ ] Роли/пользователи вместо одного shared admin token; ротация ingest/admin secrets.
- [ ] Basic rate limiting, audit/log policy, raw evidence retention и backup/restore runbook.
- [ ] Endpoint last-seen policy: `REQUIRES_VERIFICATION`, без автоматического вывода о пропаже или краже.
- [ ] Заменить user-level Scheduled Tasks на управляемый service/deployment способ для постоянной работы независимо от интерактивной сессии.

### Не входит в первую часть

- Vision Inventory / Grounding DINO, RTSP, фото помещений;
- QR, mobile, 1C, Excel, AD, Linux/macOS;
- custom agent, remote desktop, helpdesk, automatic theft detection.

## Критерий завершения первой части

Первая часть считается завершённой как demo MVP, когда оператор может без ручной работы с БД выполнить полный сценарий через UI/API: получить inventory реального или sanitized устройства, связать его с Asset, принять baseline, показать change RAM/SSD и один Incident с evidence, зафиксировать решение, отдельно принять new baseline и показать, что duplicate scan не создаёт новый incident.
