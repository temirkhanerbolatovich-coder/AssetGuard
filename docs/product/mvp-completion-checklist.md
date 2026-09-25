# AssetGuard MVP v0.1 — чек-лист завершения

Дата актуализации: 2026-09-25. Чек-лист включает computer inventory MVP, PDF/OCR импорт, демонстрационный AssetGuard Vision vertical slice и физический обход кабинета.

## Текущая оценка

- Демонстрационный MVP через native GLPI transport и explicit bridge: **готов**.
- Native GLPI Agent 1.19 `PROLOG → INVENTORY` проверен реальным компьютером через production HTTPS endpoint.
- Постоянный Oracle Cloud deployment с DuckDNS и TLS работает; локальный encrypted restore rehearsal выполнен, off-site recovery остаётся незакрытым.

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
| Dashboard | Готово | Attention-first обзор, поиск/фильтры, связанные и непривязанные устройства, полная карточка Agent-данных, baseline, читаемое «Было → Стало», incidents и timeline. |
| AssetGuard Vision | Готово для demo | Image upload, Grounding DINO, bounding boxes, counts, baseline, comparison, `WARNING` и history; кабинет связан с локацией и доступ фильтруется. RTSP и связка каждой detection с endpoint остаются будущим этапом. |
| Иерархия и права локаций | Частично | Организация → корпус → этаж → кабинет, grants VIEWER/EDITOR и единая карточка кабинета с имуществом, Agent, Vision, инцидентами, физическими обходами и историей работают; полный tenant-route matrix ещё нужен. |
| Физический обход | Готово для кабинета | ADMIN/EDITOR отмечает каждую позицию как присутствующую, отсутствующую или повреждённую; акт хранит количества, комментарии, исполнителя и серверное время. Для проблемы автоматически создаётся инцидент с решениями «проверка / перемещение / ремонт / списание / не подтвердилось». Акты и решения append-only. |
| Перемещение и списание | Готово | Подтверждённая операция меняет кабинет/остаток/статус, частично разделяет только групповые позиции, проверяет доступ к обеим локациям и формирует PDF-акт. |
| Background demo | Готово | User-level demo tasks и production Compose deployment с restart policy. |
| Local package | Готово | ZIP без secret/database/log data, startup scripts и documentation. |
| GitHub | Готово | Public repository: `temirkhanerbolatovich-coder/AssetGuard`. |
| Automated tests | Готово | Disposable PostgreSQL, JSON/native inventory, Vision workflow, auth lifecycle, identity conflict и Playwright browser E2E; GitHub Actions workflow. |
| Бесплатный demo deployment | Готово | Docker Compose + Cloudflare Quick Tunnel, временный публичный HTTPS URL без домена. |
| Encrypted backup | Готово локально | AES-256-GCM backup, restore и optional off-site copy на диск или `rclone`; fresh local restore rehearsal passed 2026-09-24, off-site здесь не настроен. |
| Excel/PDF импорт и экспорт | Готово для поддерживаемых ведомостей | PDF разбирается постранично; сканы — через локальный Tesseract OCR. Перед записью можно проверить все строки, искать, листать по 25 позиций, видеть create/update и исключать строки. Пустые формы и неподтверждённые сводные данные не превращаются в фиктивный реестр. |

## Оставшаяся работа

### P0 — demo MVP

- [x] Admin API: endpoint list/detail, snapshot list/detail, raw inventory list/detail, Asset update.
- [x] Dashboard: last seen/status, поиск и фильтры, полные Agent-данные, адаптивная карточка, capacity presentation, evidence «Было → Стало» и читаемый timeline.
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
- [~] Deployment acceptance: постоянный Oracle Cloud host, DuckDNS и публичный TLS проверены; restore rehearsal на выбранном off-site storage ещё не выполнен.
- [x] Native GLPI Agent 1.19 protocol spike и `DirectGlpiAgentAdapter`.
- [x] Browser E2E через Playwright/Chromium в GitHub Actions.
- [x] Optional real Grounding DINO CI smoke job: ручной и еженедельный workflow с настоящей моделью и demo-кадром.
- [x] Isolated encrypted-backup restore rehearsal: отдельный disposable PostgreSQL без опубликованных портов, проверка Alembic revision и entity counts; успешно выполнен локально 2026-09-24.
- [x] PDF import preview: все найденные строки выдаются API; применение по-прежнему только после явного подтверждения, отдельные строки можно исключить.

### За пределами текущего demo

- RTSP/camera scheduler, quality gate, multi-frame aggregation и `ANOMALY` confirmation;
- QR-запуск мобильного обхода; подтверждаемые перемещение и списание с PDF-актом уже работают;
- 1С/AD integrations, Linux/macOS Agent, полный matrix-тест tenant/location границ всех admin API;
- связывание каждой Vision detection с конкретным endpoint/asset;
- custom agent, remote desktop, helpdesk, automatic theft detection.

## Критерий завершения первой части

Demo MVP считается завершённым, когда оператор может без ручной работы с БД выполнить два сценария через UI/API: (1) получить inventory устройства, связать его с Asset, принять baseline, показать hardware change и Incident с evidence; (2) загрузить фото помещения, увидеть bounding boxes/counts, сохранить Vision baseline и получить `WARNING` при расхождении повторного scan.
