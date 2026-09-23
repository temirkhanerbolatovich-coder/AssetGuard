# AssetGuard MVP v0.1 — сохранённые требования

Источник: пользовательское ТЗ `AssetGuard MVP v0.1 — Technical Requirements`, полученное 23.09.2026. Этот файл — структурированная, неисполнительная фиксация требований. При расхождении с исходным ТЗ приоритет у исходного текста.

## 1. Зафиксированное направление

- Collector: неизменённый GLPI Agent.
- Backend: собственный AssetGuard.
- База данных: PostgreSQL; на MVP raw inventory допустимо хранить в JSONB.
- Архитектура: modular monolith, без микросервисов.
- Цель: Continuous Asset Control, а не клон GLPI.
- Вертикальный сценарий: `Inventory → Snapshot → Baseline → Change Detection → Incident → Decision → History`.

## 2. Гипотеза и демонстрационный сценарий

Система должна принять фактическую конфигурацию Windows-PC, сохранить доверенный baseline, найти последующее изменение RAM/SSD, создать объяснимый ChangeEvent и один Incident, позволить администратору принять решение, при необходимости явно сменить baseline и показать audit/history.

Эталонная демонстрация:

1. PC-001 сообщает RAM A123 и B456, SSD S991.
2. Создаётся Snapshot #1; администратор принимает его как baseline.
3. PC-001 сообщает RAM A123 и SSD S991 без B456.
4. Создаётся Snapshot #2; baseline сравнивается с ним.
5. Создаются `COMPONENT_REMOVED` для RAM B456 и один Incident.
6. Администратор классифицирует факт; решение попадает в history.
7. При подтверждённом изменении администратор отдельно принимает current snapshot как новый baseline.
8. Повторный identical scan создаёт ноль новых ChangeEvent/Incident.

## 3. Состояния и baseline

- `OBSERVED`: сведения, сообщённые GLPI Agent.
- `BASELINE`: доверенное техническое состояние для сравнения.
- `EXPECTED`: ожидаемое организацией состояние; MVP допускает минимальную модель.
- `VERIFIED_PHYSICAL`: человеческое подтверждение; не входит в MVP, но архитектурно должно быть расширяемо.

Критическое правило: новый snapshot никогда не становится baseline автоматически. При unresolved RAM removal старый baseline продолжает содержать исходную конфигурацию. Baseline меняется только явным административным/политическим решением.

Одновременно у `ManagedEndpoint` максимум один `ACTIVE` baseline. Статусы baseline: `ACTIVE`, `SUPERSEDED`, `REJECTED`. Первый полный snapshot — только candidate до `Accept as Baseline`.

## 4. Границы интеграции

Primary target: `GLPI Agent → HTTPS inventory payload → AssetGuard Inventory Gateway` без модификации агента.

Перед основной реализацией требуется technical spike, подтверждающий:

- direct HTTP submission;
- реальный payload и версии;
- authentication;
- full/partial inventory semantics;
- retry behavior;
- agent identity;
- compatibility/version behavior;
- RAM module serial/slot, storage serial, SMBIOS UUID, motherboard serial, monitor EDID;
- hostname-change behavior и ресурсные измерения.

Fallback, если direct ingestion требует имитировать недокументированное GLPI server behavior:

`GLPI Agent → GLPI 11 → GLPI API → AssetGuard GLPI Adapter → AssetGuard Core`.

GLPI остаётся sidecar/reference backend. AssetGuard владеет собственными `RawInventory`, snapshots, baseline, events, incidents и history. Внутреннюю БД GLPI использовать как основную БД AssetGuard запрещено.

## 5. Source abstraction

Нужен интерфейс `InventorySourceAdapter`.

- Первая реализация: `DirectGlpiAgentAdapter`.
- Fallback: `GlpiApiAdapter`.
- Возможные будущие адаптеры: `OcsApiAdapter`, `FleetAdapter`, `ManualImportAdapter`.
- Canonical AssetGuard model не зависит от внутренних GLPI ID.

## 6. Domain entities

### Organization

Одна организация в MVP: `Id`, `Name`, `CreatedAt`.

### Asset

Учётный физический объект: `Id`, `OrganizationId`, `InventoryNumber`, `Name`, `AssetType`, `Status`, `Room`, `Notes`, `CreatedAt`, `UpdatedAt`.

AssetType MVP: `Desktop`, `Laptop`, `Other`. `InventoryNumber` уникален в Organization.

### ManagedEndpoint

Техническая identity устройства с agent, отдельная от Asset: `Id`, nullable `AssetId`, `Source`, `SourceAgentId`, `Hostname`, `LastSeenAt`, `Status`, `CreatedAt`, `UpdatedAt`.

Статусы: `ONLINE`, `OFFLINE`, `REQUIRES_VERIFICATION`, `IDENTITY_CONFLICT`.

### EndpointIdentifier

Много идентификаторов на endpoint: `Id`, `ManagedEndpointId`, `IdentifierType`, `RawValue`, `NormalizedValue`, `Confidence`, `FirstSeenAt`, `LastSeenAt`, `IsActive`.

Types: `SMBIOS_UUID`, `BIOS_SERIAL`, `CHASSIS_SERIAL`, `MOTHERBOARD_SERIAL`, `AGENT_ID`, `MACHINE_GUID`, `MAC_ADDRESS`, `HOSTNAME`.

Confidence: `HIGH`, `MEDIUM`, `LOW`, `UNKNOWN`. Hostname не является основным уникальным идентификатором.

### RawInventory

Каждый payload сохраняется до нормализации и immutable: `Id`, `ManagedEndpointId`, `Source`, `SourceVersion`, `SchemaVersion`, `ReceivedAt`, `PayloadHash`, JSONB `Payload`, `InventoryType`, `ProcessingStatus`, `Error`.

InventoryType: `FULL`, `PARTIAL`, `UNKNOWN`. ProcessingStatus: `RECEIVED`, `PROCESSED`, `FAILED`.

### HardwareSnapshot

Нормализованное наблюдение: `Id`, `ManagedEndpointId`, `RawInventoryId`, `CapturedAt`, `CreatedAt`, `SnapshotType`, `Completeness`, `NormalizerVersion`.

`Completeness` обязан описывать реально присутствующие/валидные категории. SnapshotType: `FULL`, `PARTIAL`.

### ComponentObservation

Факт наблюдения компонента в конкретном snapshot: `Id`, `HardwareSnapshotId`, `ComponentType`, nullable `ComponentIdentityId`, `Manufacturer`, `Model`, `SerialNumber`, `PartNumber`, `Capacity`, `Slot`, `SourceKey`, `Confidence`, JSONB `RawData`.

Types MVP: `CPU`, `MOTHERBOARD`, `RAM`, `STORAGE`, `GPU`, `NETWORK`, `MONITOR`. Приоритет детекции: RAM и STORAGE.

### ComponentIdentity

Отдельна от observation; это гипотеза о физически той же детали: `Id`, `ComponentType`, `CanonicalSerial`, `Manufacturer`, `Model`, `PartNumber`, `IdentityConfidence`, `CreatedAt`.

### Baseline, ChangeEvent, Incident, IncidentDecision, AssetHistoryEntry

- `Baseline`: endpoint, snapshot, status, actor/time accept/supersede, reason.
- `ChangeEvent`: asset/endpoint, baseline/current snapshots, component, previous/current observations, type, confidence, severity, status, evidence, detection time, detector version, deterministic dedup key.
- `Incident`: workflow над фактом; asset, status, severity, title/description, timestamps.
- `IncidentDecision`: append-only decision, comment, actor, timestamp.
- `AssetHistoryEntry`: append-only unified timeline с event, text, timestamp, related entity и metadata.

## 7. Identity and normalization

Confidence component identity:

- HIGH: valid non-placeholder unique serial/WWN, совместимый с type/model/vendor.
- MEDIUM: stable composite `manufacturer + model/part + capacity + slot`.
- LOW: только model/capacity/slot или эквивалент.
- UNKNOWN: доказательств недостаточно.

Normalizer обязан:

- trim whitespace, нормализовать case только где безопасно;
- нормализовать serial representation и capacity units;
- сортировать unordered collections;
- хранить original/raw values;
- различать missing, empty и collector error;
- распознавать расширяемый denylist: empty, `00000000`, all-zero, all-F, `Unknown`, `Default string`, `To Be Filled By O.E.M.` и generic OEM placeholders.

Invalid/generic identifier не может давать HIGH confidence.

## 8. Diff and event rules

Сравнение: `ACTIVE BASELINE` против `CURRENT SNAPSHOT`; результат — `ChangeEvent[]`.

Matching order:

1. HIGH-confidence identity.
2. Validated serial + compatible type/vendor/model.
3. Stable source-native identifier.
4. Composite fingerprint.
5. Slot-aware matching.
6. При неуверенном match: REMOVED old + ADDED new; не утверждать `REPLACED`/`MOVED`.

Event types MVP: `COMPONENT_ADDED`, `COMPONENT_REMOVED`, `COMPONENT_CHANGED`, `COMPONENT_REPLACED`, `DEVICE_IDENTITY_CHANGED`, `HOSTNAME_CHANGED`.

`COMPONENT_MOVEMENT_CANDIDATE` — только optional experimental; подтверждённое перемещение автоматически не создаётся.

Каждый event обязан иметь JSONB evidence с previous/current values, причинами comparison и IDs сравниваемых snapshots. Все автоматические выводы должны быть объяснимыми.

Deduplication обязательна: повторное unresolved изменение создаёт/обновляет тот же workflow, а не десять incident. DedupKey — deterministic.

## 9. Partial inventory and noise safety

Отсутствие компонента в PARTIAL inventory никогда не означает `REMOVED`. Diff допускается только в категориях, помеченных complete/valid для текущего snapshot.

- RAM/internal storage с HIGH confidence при full/complete scan можно показать сразу.
- Monitors/weak peripherals не должны создавать тяжёлый incident по одному слабому observation.
- Policy interface/configuration должна позволить future rule `two consecutive missing observations`.
- Каждый event содержит confidence `HIGH`, `MEDIUM`, `LOW` или `UNKNOWN`.

## 10. Incident workflow

ChangeEvent — технический факт; Incident — workflow.

Statuses: `OPEN`, `UNDER_REVIEW`, `RESOLVED`, `DISMISSED`.

Классификации: `PLANNED_MAINTENANCE`, `UPGRADE`, `REPAIR`, `AUTHORIZED_CHANGE`, `COMPONENT_TRANSFER`, `UNKNOWN`, `REQUIRES_INVESTIGATION`, `FALSE_POSITIVE`.

Решение не перезаписывает историю: каждое хранится отдельным IncidentDecision. При закрытии Incident пользователь отдельно решает, принимать ли current state как baseline. При принятии старый baseline становится `SUPERSEDED`, новый — `ACTIVE`.

## 11. History and offline behavior

Timeline Asset должен включать как минимум:

- creation Asset;
- endpoint link;
- baseline accepted/changed;
- hardware change detected;
- incident created/classified/resolved;
- hostname changed;
- endpoint requires verification.

History append-only в MVP.

Отсутствие telemetry не означает пропажу устройства/кражу/отсутствие железа. По configurable `LastSeenAt` threshold endpoint получает `REQUIRES_VERIFICATION`. Нельзя использовать theft/stolen/missing hardware как автоматический диагноз.

## 12. API and UI scope

REST API:

- Assets: list/create/get/update.
- Endpoints: list/get/link to asset.
- Inventories: internal agent endpoint определяется только после spike; admin list/get inventory.
- Snapshots: list/get.
- Baseline: get/accept snapshot.
- Changes: list/get.
- Incidents: list/get/decision/resolve.
- Asset history: get.

Minimal UI:

- Dashboard: counts Assets, Endpoints online/requires verification, detected changes/open incidents, recent changes.
- Assets table: inventory number, name, hostname, type, endpoint status, last seen, incidents.
- Asset details: header/status, current hardware, baseline-vs-current, open incidents, history.
- Incident page: evidence, previous/current observation, confidence/time, classification/comment, separate Resolve and Accept Current State as New Baseline actions.

## 13. Security, privacy, logging

MVP security: HTTPS, normal certificate validation for GLPI Agent, authenticated/authorized admin API and UI, payload limits, schema validation, basic rate limiting, audit trail, secrets outside source, no DB exposure. `NO_SSL_CHECK` запрещён для production.

Privacy: не собирать без причины user files, browser history, processes, arbitrary registry, passwords, product keys или personal documents.

Backend logs: received/rejected inventory, normalization errors, identity conflicts, snapshots, diff/event/incident creation, baseline accepted, incident resolved. Secrets в логи не попадают.

## 14. Mandatory fixtures/tests

Sanitized fixtures:

1. RAM A + RAM B + SSD X.
2. Same PC, RAM A + SSD X → RAM B `COMPONENT_REMOVED`.
3. RAM A + B + SSD X then SSD Y → X removed + Y added; replacement только при достаточных evidence.
4. Identical scan → zero ChangeEvents.
5. PARTIAL SOFTWARE inventory → zero hardware removal events.
6. Hostname changed → `HOSTNAME_CHANGED`, без нового Asset.

## 15. Definition of Done

Готовность MVP доказывается сквозным сценарием: установить upstream unmodified GLPI Agent; принять full inventory; сохранить immutable raw payload; создать normalized snapshot; связать endpoint с asset/inventory number; принять baseline; изменить RAM/SSD или подать fixture; принять новый snapshot; автоматически создать change event и ровно один incident; показать его в dashboard и baseline/current на asset details; классифицировать и записать решение в history; явно принять новый baseline; получить identical scan без новых events.

## 16. Out of scope

Не входят: QR/mobile, 1C, Excel, AD integration, network discovery, Linux/macOS, custom Windows agent, AI, remote desktop, helpdesk, patch/antivirus/software deployment, license management, automatic theft detection, universal component tracking, complex multi-tenancy, billing, advanced analytics.

## 17. Priority and engineering constraints

P0: GLPI integration, RawInventory, normalization, Asset/ManagedEndpoint, snapshot, baseline, RAM/storage identity, diff, events, incidents, history, minimal UI.

P1: CPU/GPU/motherboard/monitor presentation, offline policy, better confidence, movement candidates, dashboard improvements.

P2: QR/physical verification/inventory sessions, Excel, Kazakhstan workflow, 1C.

Engineering rules:

1. Не выдумывать GLPI Agent data.
2. Missing field не считать removed component.
3. Не связывать Asset identity только с hostname.
4. Не менять raw inventory.
5. Не менять baseline автоматически после unresolved change.
6. Не создавать duplicate incidents.
7. Не называть change кражей.
8. Не вводить микросервисы, GLPI fork или custom collector без доказанного основания.
9. Предпочитать простую проверяемую реализацию.
10. Любое decision/detection должно иметь evidence; важные admin actions — audit/history.
11. Реальные результаты PoC приоритетнее предположений ТЗ.

## 18. Текущий режим работы

На текущем шаге разрешены только анализ, сохранение требований и read-only inspection workspace. Разработка, technical spike и планирование реализации запускаются только отдельным последующим указанием пользователя.
