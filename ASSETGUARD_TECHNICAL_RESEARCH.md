# AssetGuard — Technical Research Report

**Дата исследования:** 23 сентября 2026 г.  
**Область:** Windows-first MVP; open-source collection layer; continuous asset control.  
**Статус:** архитектурное решение, без реализации.  

## A. Executive Summary

### Рекомендация

Для проверки продуктовой гипотезы AssetGuard не следует форкать OCS, GLPI или Fleet и не следует писать собственный Windows-agent.

Оптимальный путь для PoC/MVP:

1. **Использовать GLPI Agent без модификаций как Windows collector.** Он уже собирает нужные для демонстрации данные: системный UUID/serial, motherboard, CPU, отдельные RAM-модули, накопители, сетевые адаптеры, мониторы/EDID, Windows и ПО. Формат GLPI Inventory формально описан JSON Schema и включает нужные поля для RAM, storage, monitors, network и software ([официальная схема](https://github.com/glpi-project/inventory_format/blob/main/inventory.schema.json)).
2. **В Phase 0 принимать JSON inventory напрямую в небольшой AssetGuard Ingestion Gateway**, сохраняя оригинальный payload неизменяемым. GLPI Agent умеет писать inventory локально и отправлять его совместимому серверу; его серверный протокол необходимо подтвердить коротким wire-level PoC до принятия окончательного решения ([agent CLI/targets](https://github.com/glpi-project/glpi-agent/blob/develop/bin/glpi-agent), [GLPI inventory format](https://github.com/glpi-project/inventory_format)).
3. **Держать GLPI 11 как fallback/reference backend, а не как обязательную часть конечной архитектуры.** Если direct ingestion окажется нестабильным или потребует имитировать слишком много GLPI-протокола, MVP должен использовать неизменённые GLPI Agent + GLPI, а AssetGuard — читать данные через API. У GLPI 11 есть OAuth2 API, inventory scope и REST/GraphQL; legacy API также умеет отдавать computer вместе с components/software/logs ([API v2](https://help.glpi-project.org/documentation/modules/configuration/general/api/restful-api-v2), [API v1](https://help.glpi-project.org/documentation/modules/configuration/general/api/api)).
4. **Собственными сделать продуктовые слои:** append-only snapshots, normalization, confidence-aware identity resolution, diff/change events, incident workflow, expected/accounting state, physical verification и history timeline.

### Почему не «весь GLPI»

GLPI уже покрывает ITAM, assets, locations, users, inventory, history и tickets; это означает заметное продуктовое пересечение с AssetGuard ([GLPI assets](https://help.glpi-project.org/documentation/modules/assets), [computers](https://help.glpi-project.org/documentation/modules/assets/computers)). Но его history — журнал изменений текущих объектов, а не специально спроектированный immutable snapshot + evidence + confidence + incident lifecycle. AssetGuard имеет смысл только как более узкий продукт: **сопоставление expected / technical / physical state и доказуемая обработка изменений**, а не ещё один CMDB/ITSM.

### Главный архитектурный тезис

Нельзя строить detection только по текущему состоянию стороннего backend. AssetGuard должен сохранять каждый полученный raw inventory, нормализованный snapshot и результат сравнения. Это обеспечивает повторный расчёт после исправления нормализатора, аудит и объяснимость.

---

## B. Comparison

### B1. Итоговая сравнительная матрица

| Критерий | OCS Inventory NG 2.x | OCS 3.0 | GLPI Agent + GLPI | Fleet + osquery | Snipe-IT |
|---|---|---|---|---|---|
| Windows hardware coverage | Высокое | Потенциально высокое, но новая реализация | **Очень высокое** | Высокое, но пробел по Windows-мониторам | Нет agent collection |
| RAM modules/slot/serial | Да | Заявлено новой моделью; нужен PoC | **Да** | Да, `memory_devices` портирован на Windows | Manual/API only |
| Disk model/capacity/serial | Да | Да по модели проекта; нужен PoC | **Да** | Да | Manual/API only |
| Monitor model/serial | Да, EDID | Нужен PoC | **Да, EDID + vendor fixes** | **Нет штатной Windows-таблицы**; feature request открыт | Manual/API only |
| Windows / software | Да | Да | **Да** | **Да** | Manual/API only |
| API | Read-oriented REST; polling | Современный DRF REST | REST v1, OAuth2 REST/GraphQL v2 | **Зрелый REST + result webhooks** | Зрелый REST |
| Generic immutable snapshots | Нет | Не подтверждено | Нет | Query result logs возможны, но не AssetGuard snapshots | Нет |
| Component change incidents | Нет | Не подтверждено | History есть, incident semantics нет | Можно конструировать queries/policies, но готового hardware diff нет | Asset history, без detection |
| Windows deployment | EXE, service, silent, GPO | Новый EXE/Inno, service, silent | **MSI, service/task, silent, GPO/ADMX** | MSI/fleetd, service, centralized config | N/A |
| Offline/retry | Да | Да, подтвердить pilot | **Да, backoff/random delay** | Да | N/A |
| Extensibility | Agent plugins/server plugins, legacy | Django/Vue extensions | Agent modules, plugins, schema/API | **SQL queries/extensions/webhooks** | API/webhooks |
| Maturity for this use | Agent mature; server legacy | **RC, не production baseline** | **Mature collector + mature ITAM** | Mature endpoint platform, heavier | Mature ITAM, not collector |
| License | GPL-2.0 family | GPL-3.0 | Agent GPL-2.0+; GLPI GPL-3.0 | osquery Apache-2.0 OR GPL-2.0; Fleet open core/MIT free portion | AGPL-3.0 |
| Suitability | Хороший запасной вариант | Наблюдать, не брать в MVP | **Лучший collector; backend optional** | Хорош для security/endpoint telemetry, не лучший hardware foundation | Полезен как benchmark продукта, не foundation |

### B2. Что реально собирается на Windows

Легенда: **✓** — штатно; **△** — частично/зависит от firmware, драйвера или дополнительного query; **—** — штатного источника для Windows не найдено.

| Поле | OCS 2.x Windows Agent | GLPI Agent | Fleet/osquery |
|---|---:|---:|---:|
| hostname | ✓ | ✓ | ✓ `system_info` |
| manufacturer / device model | ✓ | ✓ | ✓ |
| device serial | ✓ | ✓ | ✓ `hardware_serial` |
| SMBIOS UUID | ✓ | ✓ | ✓ `uuid` |
| motherboard manufacturer/model/serial | ✓ | ✓ | ✓ `board_*` |
| CPU | ✓ | ✓ | ✓ brand/cores/sockets |
| GPU | ✓ | ✓ | ✓ model/manufacturer/driver |
| GPU serial | △ редко доступен | △ schema не делает его надёжной identity | — в `video_info` serial отсутствует |
| total RAM | ✓ | ✓ | ✓ |
| individual RAM modules | ✓ | ✓ | ✓ `memory_devices` |
| RAM slot/bank | ✓ | ✓ caption/slot | ✓ locator/bank locator |
| RAM manufacturer | △ зависит от SMBIOS | ✓ если firmware сообщает | ✓ если SMBIOS сообщает |
| RAM part number | △ | ✓ model/part representation | ✓ `part_number` |
| RAM serial | ✓ если firmware сообщает | ✓ если firmware сообщает | ✓ если SMBIOS сообщает |
| disks model/capacity/serial | ✓ | ✓ | ✓ `disk_info` |
| network adapters / MAC | ✓ | ✓ | ✓ |
| monitors manufacturer/model/serial | ✓, EDID | **✓, EDID** | **— на Windows** |
| Windows version/build | ✓ | ✓ | ✓ `os_version` |
| installed software | ✓ | ✓ | ✓ `programs` и доп. tables |

Подтверждения:

- OCS server mapping явно хранит multi-valued monitor и storage records, включая serial, capacity/model/firmware, и включает diff flags ([OCS Map.pm](https://github.com/OCSInventory-NG/OCSInventory-Server/blob/master/Apache/Ocsinventory/Map.pm)); Windows agent парсит EDID и serial мониторов ([EDID.cpp](https://github.com/OCSInventory-NG/WindowsAgent/blob/master/SysInfo/EDID.cpp)); пример RAM inventory содержит capacity, slot и serial ([issue с фактическим XML](https://github.com/OCSInventory-NG/WindowsAgent/issues/183)).
- GLPI schema содержит motherboard/system serial, отдельные memories с slot/serial/model/manufacturer, storages с size/model/serial, monitors с EDID/serial/altserial, network MAC, OS и software ([schema](https://raw.githubusercontent.com/glpi-project/inventory_format/main/inventory.schema.json)). GLPI UI действительно моделирует memory serial/location, hard drive serial и network MAC ([components docs](https://help.glpi-project.org/documentation/tabs/components)).
- osquery `system_info` содержит hardware и board identity ([schema](https://github.com/osquery/osquery/blob/master/specs/system_info.table)); `memory_devices` содержит locator, manufacturer, serial и part number ([schema](https://raw.githubusercontent.com/osquery/osquery/master/specs/memory_devices.table)); `disk_info` — model/size/serial ([schema](https://raw.githubusercontent.com/osquery/osquery/master/specs/windows/disk_info.table)); `video_info` — GPU model/manufacturer, но без serial ([schema](https://raw.githubusercontent.com/osquery/osquery/master/specs/windows/video_info.table)); `os_version` — Windows build/revision ([schema](https://raw.githubusercontent.com/osquery/osquery/master/specs/os_version.table)). Windows monitor inventory остаётся открытым feature request ([osquery #7682](https://github.com/osquery/osquery/issues/7682)).

### B3. OCS Inventory NG

**OCS 2.x.** Сильные стороны — зрелый Windows agent, service mode, local/offline XML, GPO/logon deployment, hardware coverage, retry и серверная дедупликация категорий. Agent хранит local state и отправляет изменения, а server mapping имеет `writeDiff`, но это оптимизация синхронизации, не полноценная AssetGuard event model. REST API позволяет читать computer details и выбирать обновлённые после timestamp, поэтому интеграция делается polling; официальная документация прямо говорит, что POST/PUT routes не реализованы ([GET routes](https://wiki.ocsinventory-ng.org/11.Rest-API/GET-Routes/), [API introduction](https://wiki.ocsinventory-ng.org/11.Rest-API/Introduction/)).

Слабость — legacy server (Perl communication server + PHP/MySQL design), read-oriented API и собственная device identity, исторически основанная на hostname/MAC (`ocsinventory.dat`). Это неудобная база для нового продукта.

**OCS 3.0.** Архитектура стала привлекательнее: Django REST Framework, Vue и новый Dart agent. Но на дату исследования проект только выпустил **3.0.0-rc1**, новый agent предназначен строго для 3.0, а репозитории имеют малую эксплуатационную историю ([official project overview](https://github.com/ocsinventory-ng), [new agent README](https://github.com/OCSInventory-NG/OCSInventory-Agent-Rework), [new backend](https://github.com/OCSInventory-NG/OCSInventory-Server-Backend-Rework)). Для production foundation MVP это высокий риск. Его стоит повторно оценить после stable release и pilot evidence.

### B4. GLPI Agent + GLPI

GLPI Agent — наиболее подходящий collector. Он является продолжением FusionInventory, имеет активные релизы, Windows x64 MSI, local JSON/XML, partial inventory по изменившимся категориям, proxy, CA/fingerprint, client certificate, OAuth options и GPO ADMX ([releases](https://github.com/glpi-project/glpi-agent/releases), [agent options](https://github.com/glpi-project/doc-agent/blob/master/source/man/glpi-agent.rst), [ADMX](https://github.com/glpi-project/glpi-agent/blob/develop/contrib/windows/GLPI-Agent.admx)). Частичный inventory вычисляется через SHA-256 по категориям, но это экономия трафика, а не бизнес-событие ([design note](https://github.com/glpi-project/glpi-agent/discussions/592)).

GLPI backend полезен как готовый inventory receiver и reference implementation. Он уже даёт computers, inventory number, UUID, location, user, components, software, last contact и history. Но его внутреннюю БД нельзя делать контрактом AssetGuard: интеграция должна идти через version-pinned API или через собственный ingestion format.

### B5. Fleet + osquery

Fleet — зрелый API-first endpoint platform. Он даёт enrollment, centralized configuration, REST, scheduled reports, policies, result webhooks, host status и масштаб до очень больших парков. Fleet заявляет deployments до 500,000 devices; это vendor claim, не независимый benchmark ([FAQ](https://fleetdm.com/docs/get-started/faq)).

Однако для AssetGuard это более тяжёлый стек (Fleet + MySQL, а для ряда режимов Redis) и менее готовая модель именно физического hardware. Нужные данные можно собирать SQL queries, но Windows-monitor table отсутствует, GPU serial отсутствует, а snapshot/diff/incident всё равно придётся строить. Fleet рационален, если roadmap включает security posture, compliance и live endpoint queries; для демонстрации RAM removed — избыточен.

### B6. Другие кандидаты

- **Snipe-IT** — хороший эталон ITAM/QR/check-in/out/API, но не agent/hardware collector. Как foundation не подходит; как источник требований к учётному и physical workflow полезен. Код AGPL-3.0 ([official repository](https://github.com/grokability/snipe-it)).
- **FusionInventory** — не отдельный выбор: GLPI Agent является его преемником; GLPI прямо сообщает, что FusionInventory больше не поддерживается начиная с GLPI 10 ([GLPI inventory FAQ](https://help.glpi-project.org/faq/glpi/inventory)).
- **Wazuh** — сильный security/SIEM agent, но hardware component inventory не его основная задача; добавит серверную сложность без преимущества для этого MVP.
- **Open-AudIT** — близок по discovery/inventory, но уступает выбранным кандидатам по ясности open-source границы и современности интеграции; не даёт причины отказаться от GLPI Agent.

---

## C. Recommended Foundation

### Основной вариант: collector-first

**GLPI Agent (unmodified) → AssetGuard Inventory Gateway → AssetGuard Core/PostgreSQL.**

Это рекомендуемый target, но с обязательным Phase 0 gate: подтвердить direct HTTP ingestion, authentication, retry, full/partial inventory semantics и upgrade path на 5–10 разных Windows machines.

### Fallback для самого быстрого демо

**GLPI Agent → GLPI 11 → AssetGuard GLPI Adapter (polling API) → AssetGuard Core.**

Этот вариант быстрее, если direct receiver требует воспроизводить недокументированные negotiation details. Он сохраняет независимость: GLPI — sidecar service, AssetGuard владеет своей БД, snapshots и workflows.

### Не рекомендовано сейчас

- OCS 3.0 как foundation до stable/pilot.
- OCS 2.x как новый стратегический backend.
- Fleet/osquery только ради hardware inventory.
- Fork GLPI/OCS и встраивание AssetGuard в их UI/DB.
- Собственный WMI collector до фактического доказательства, что GLPI Agent не покрывает конкретные критические модели оборудования.

---

## D. Reuse vs Build

| Component | Reuse | Adapt | Build ourselves |
|---|---|---|---|
| Windows hardware collectors | GLPI Agent | Configure categories, interval | No |
| Windows service/scheduler | GLPI Agent MSI | GPO settings | No |
| Agent installer | Official MSI | Branded deployment guide only | No for MVP |
| Agent updater | GPO/SCCM/Intune/GLPI Deploy where available | Controlled rollout rings | No custom updater in MVP |
| Inventory transport | GLPI Agent HTTPS | AssetGuard-compatible ingestion or GLPI adapter | Gateway/auth envelope |
| Raw inventory format | GLPI JSON/XML | Versioned parser | Canonical schema |
| Raw payload archive | — | — | **Yes, immutable** |
| Snapshot storage | — | — | **Yes** |
| Normalization | GLPI schema as input | Vendor/default-value rules | **Yes** |
| Device identity resolution | Source identifiers | Confidence rules | **Yes** |
| Component identity | Source serial/part/slot | Confidence/fingerprint | **Yes** |
| Diff engine | — | — | **Yes** |
| Incident engine | — | — | **Yes** |
| Asset/accounting database | Optional import from GLPI/Excel | Mapping adapters | **Yes** |
| Physical verification / QR | — | — | **Yes, later** |
| Dashboard/timeline | — | — | **Yes** |
| Kazakhstan workflow | — | — | **Yes** |
| Excel import/export | Libraries | Templates/validation | **Yes, Phase 2** |
| 1C integration | 1C APIs/files | Customer mapping | **Yes, Phase 3** |

---

## E. Proposed Architecture

```text
Windows PC
  └─ GLPI Agent (unmodified upstream MSI; hash/signature verified at deployment)
       └─ HTTPS inventory push
            └─ AssetGuard Inventory Gateway
                 ├─ authenticate / rate-limit / size-limit
                 ├─ store RawInventory (immutable)
                 └─ enqueue InventoryReceived
                      └─ Normalizer
                           ├─ Canonical HardwareSnapshot
                           ├─ Identity Resolver
                           └─ Quality/Confidence annotations
                                └─ Diff Engine
                                     ├─ ChangeEvent(s)
                                     ├─ ComponentMovementCandidate(s)
                                     └─ Incident Policy Engine
                                          └─ AssetGuard API/UI

Accounting imports ───────────────┐
Physical verification / QR ───────┼─→ Asset State Reconciliation
GLPI/OCS adapters (optional) ──────┘

Storage:
PostgreSQL  — business state, canonical snapshots, events, incidents
Object/blob storage — compressed raw inventories (or PostgreSQL JSONB for MVP)
Queue/outbox — reliable asynchronous processing
```

Для MVP это должен быть **модульный монолит**, а не набор микросервисов: один backend deployment, один PostgreSQL, логические модули и transactional outbox. Gateway/worker можно разделить процессами, но не независимыми сервисами. Это быстрее, проще и достаточно до тысяч endpoints.

### Source abstraction

Ввести контракт `InventorySourceAdapter`:

- `DirectGlpiAgentAdapter` — primary PoC;
- `GlpiApiAdapter` — fallback;
- `OcsApiAdapter` — future migration/import;
- `FleetAdapter` — future security-oriented deployments;
- `Manual/ExcelAdapter` — expected state.

Canonical model не должен содержать GLPI/OCS table IDs.

---

## F. Data Flow

```text
1. Computer scan
2. Agent produces inventory payload
3. Gateway validates source, schema/version, timestamp and size
4. Raw payload stored before interpretation
5. Device identity resolver links observation to Asset/Endpoint
6. Normalizer produces ordered canonical snapshot
7. Quality rules mark missing/default/unreliable identifiers
8. Snapshot is compared with last accepted baseline
9. Diff engine emits facts: ADDED / REMOVED / CHANGED / MOVED_CANDIDATE
10. Policy engine groups facts into Incident, or suppresses expected noise
11. Administrator classifies/authorizes the change
12. Baseline policy accepts, rejects or supersedes the new state
13. AssetHistory receives immutable timeline entries
```

### Важное различие состояний

- `OBSERVED`: что сообщил agent.
- `EXPECTED`: что утверждает бухгалтерия/организация.
- `VERIFIED_PHYSICAL`: что подтвердил человек.
- `BASELINE`: выбранное доверенное техническое состояние для сравнения.

Новый snapshot не должен автоматически становиться baseline при критическом unresolved change; иначе повторное сканирование «узаконит» исчезнувший компонент.

---

## G. Data Model

### Core entities

| Entity | Назначение |
|---|---|
| `Organization` | Tenant/организация |
| `Site`, `Building`, `Floor`, `Room` | Иерархия размещения |
| `Person` / `ResponsibleAssignment` | МОЛ и период ответственности |
| `Asset` | Учётный физический объект; inventory number и тип |
| `ManagedEndpoint` | Agent-bearing technical endpoint linked to Asset |
| `EndpointIdentifier` | UUID, BIOS serial, agent ID, MachineGuid, hostname, MAC с validity/confidence |
| `RawInventory` | Неизменённый payload, hash, source, received_at |
| `HardwareSnapshot` | Нормализованное observed state |
| `ComponentObservation` | Component in a specific snapshot |
| `ComponentIdentity` | Probabilistic/confirmed durable component identity |
| `ChangeEvent` | Atomic fact between snapshots |
| `Incident` | Workflow container over one/more change events |
| `IncidentDecision` | Classification, comment, actor, timestamp |
| `Baseline` | Accepted snapshot or per-component expected baseline |
| `PhysicalVerification` | Human confirmation of presence/location |
| `InventorySession` | Physical inventory campaign |
| `ExpectedAssetState` | Accounting/imported expectations |
| `AssetHistoryEntry` | Unified immutable timeline projection |

### Relationships

```text
Organization 1─* Asset 1─0..1 ManagedEndpoint
Asset *─1 Room
Asset 1─* ResponsibleAssignment *─1 Person
ManagedEndpoint 1─* EndpointIdentifier
ManagedEndpoint 1─* HardwareSnapshot 1─* ComponentObservation
ComponentIdentity 1─* ComponentObservation
HardwareSnapshot(prev,next) 1─* ChangeEvent *─0..1 Incident
Asset 1─* Baseline
InventorySession 1─* PhysicalVerification *─1 Asset
Asset 1─* ExpectedAssetState
Asset 1─* AssetHistoryEntry
```

`ComponentObservation` и `ComponentIdentity` нельзя объединять: одно — факт конкретного сканирования, второе — гипотеза о том, что наблюдения относятся к одной физической детали.

---

## H. Hardware Identity Reliability

### H1. Device identity

Не использовать один «магический» ID. Хранить несколько identifiers и принимать решение по правилам.

| Signal | Confidence | Поведение |
|---|---|---|
| Verified inventory number / QR link | HIGH (accounting) | Stable until manual reassignment |
| SMBIOS UUID, non-zero/non-default and not duplicated | HIGH | Usually survives Windows reinstall; often changes with motherboard |
| Chassis/BIOS serial, valid and unique | HIGH | Usually survives OS reinstall; quality depends on OEM |
| Agent-generated UUID | MEDIUM/HIGH for installation | May change on reinstall; may duplicate through bad imaging |
| Windows MachineGuid | MEDIUM for OS installation | Changes on generalized reinstall; may duplicate after cloning |
| Motherboard serial | MEDIUM | Changes with board; often generic/missing on white-box PCs |
| Stable set of MAC addresses | LOW/MEDIUM | NIC/dock/VM changes; spoofable |
| Hostname | LOW | Administrative label, freely changed |

Microsoft documents that `Win32_ComputerSystemProduct.UUID` comes from SMBIOS and can be all-zero when unavailable ([Microsoft](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-computersystemproduct)). SMBIOS UUID/serial are intended to identify a machine, but firmware vendors populate them ([Microsoft SMBIOS guidance](https://learn.microsoft.com/en-us/windows-hardware/drivers/bringup/smbios)). A cloned installation can duplicate MachineGuid, while Sysprep generalization resets installation-specific values ([Microsoft discussion](https://learn.microsoft.com/en-au/answers/questions/1489139/identifying-unique-windows-installation)).

#### Expected transitions

- **Windows reinstall:** same Asset if strong hardware identifiers match; create new agent/install identity.
- **Motherboard replacement:** never auto-create a new Asset solely because UUID/board serial changed. Raise `DEVICE_IDENTITY_CHANGED`; require match by inventory number/QR/administrator.
- **Hostname change:** update weak identifier and history; no new Asset.
- **Disk clone:** possible duplicate MachineGuid/agent state. Detect simultaneous use of same identifier on different strong hardware fingerprints; quarantine linkage.

### H2. Component identity

| Component | Typical confidence | Notes |
|---|---|---|
| SSD/HDD/NVMe | HIGH when manufacturer serial/WWN valid | Best movement candidate; virtual/USB bridges may hide or rewrite serial |
| RAM module | HIGH only with valid non-generic serial; otherwise MEDIUM/LOW | SMBIOS exposes serial, manufacturer, part and locator, but OEM may return blank/default ([Win32_PhysicalMemory](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-physicalmemory)) |
| Monitor | MEDIUM, sometimes HIGH | EDID serial may be blank, `00000000`, truncated, encoded differently or duplicated across units; GLPI issues demonstrate this ([example](https://github.com/glpi-project/glpi-agent/issues/1040)); Microsoft confirms EDID-backed fields ([WmiMonitorID](https://learn.microsoft.com/en-us/windows/win32/wmicoreprov/wmimonitorid)) |
| Motherboard | MEDIUM/HIGH on OEM systems | Serial may be generic/default; replacement is also a device-identity event ([Win32_BaseBoard](https://learn.microsoft.com/en-us/windows/win32/cimwin32prov/win32-baseboard)) |
| GPU | LOW | Windows inventory normally gives model/PNP ID, not unique board serial |

### H3. Confidence algorithm

- `HIGH`: normalized serial/WWN present, not denylisted, unique across active estate, plus compatible manufacturer/model.
- `MEDIUM`: stable composite (manufacturer + part/model + capacity + slot/PNP) or a serial with known ambiguity.
- `LOW`: model/capacity/slot only.
- `UNKNOWN`: insufficient or contradictory evidence.

Denylist values include empty, all-zero/all-F, `To Be Filled By O.E.M.`, `Default string`, `Unknown`, repeated system-wide placeholders and vendor-specific known defaults.

Movement detection rules:

- Auto-create a **movement candidate**, not a confirmed movement.
- HIGH identifier seen on A then B, with non-overlapping observation windows → HIGH candidate.
- Same identifier simultaneously on A and B → duplicate/spoof/data-quality incident, not movement.
- MEDIUM/LOW → require administrator confirmation; never silently reassign component ownership.

---

## I. Snapshot and Change Detection

### Canonicalization before diff

- Normalize whitespace/case/serial encodings, but preserve raw values.
- Sort unordered collections by stable comparison key.
- Separate `not reported`, `not detectable`, `not present`, and `collector error`.
- Treat partial inventory explicitly; absence from a partial category is not removal.
- Record collector version/schema version and per-category completeness.

### Matching order

1. Exact HIGH identity.
2. Exact validated serial + compatible type/vendor/model.
3. Stable source-native key, if its lifecycle is understood.
4. Weighted fingerprint.
5. Slot-aware match for non-unique components.
6. Otherwise: one removal + one addition, not an asserted replacement/movement.

### ChangeEvent

Minimum fields:

`event_type`, `asset_id`, `component_type`, `previous_observation_id`, `current_observation_id`, `detected_at`, `confidence`, `evidence`, `severity`, `status`, `detector_version`, `dedup_key`.

### Noise controls

- Require two consecutive missing observations for low-confidence/occasionally disconnected devices such as monitors.
- Do not apply this delay to high-confidence internal disk/RAM removal unless scan quality is degraded.
- Suppress pure formatting/order changes.
- Maintenance window and approved change can correlate events but must not delete facts.
- Offline host creates `REQUIRES_VERIFICATION` only after policy threshold; absence of reports is not component absence.

---

## J. API, Deployment, Performance and Scale

### API/integration

- **OCS 2.x:** REST GET, updated-since polling; no general POST/PUT integration contract in documented API.
- **OCS 3.0:** modern DRF REST, but release maturity is the blocker.
- **GLPI 11:** OAuth2 REST v2 + read-only GraphQL wrapper; inventory client-credentials scope; legacy REST can return components/software/logs.
- **Fleet:** broad REST and result/activity/status webhooks; best API ergonomics of the candidates.

### Windows deployment

**GLPI Agent:** official MSI/portable packages, silent install, Windows service/task modes, official deployment VBS and ADMX, proxy, CA file/system keystore, certificate fingerprint, optional client certificate ([deployment script](https://github.com/glpi-project/glpi-agent/blob/develop/contrib/windows/glpi-agent-deployment.vbs), [network/TLS options](https://github.com/glpi-project/doc-agent/blob/master/source/man/glpi-agent.rst)). Disable the embedded HTTP listener for an outbound-only MVP unless remote-trigger inventory is explicitly required.

**OCS 2.x:** EXE, Windows service, standalone/GPO/logon script, local offline inventory, HTTP/HTTPS outbound communication ([official setup](https://wiki.ocsinventory-ng.org/03.Basic-documentation/Setting-up-the-Windows-Agent-2.x-on-client-computers/)).

**Fleet/osquery:** MSI/Windows SYSTEM service and centralized options. osquery recommends enterprise deployment tools such as SCCM for fleets ([Windows install](https://github.com/osquery/osquery/blob/master/docs/wiki/installation/install-windows.md)).

### Scale recommendation

| Size | Recommendation |
|---:|---|
| 10 | Single backend + PostgreSQL; synchronous normalize/diff acceptable |
| 100 | Background worker/outbox; randomized scans; daily full inventory |
| 1,000 | Queue, raw payload compression, indexed snapshots/events, staged agent rollout, polling cursor if using GLPI |
| 10,000 | Partitioning/retention, separate workers, HA ingress, backpressure, load tests with production-shaped payloads; reconsider direct push vs broker |

Do not extrapolate Fleet’s vendor scale claim to AssetGuard. Its own ingestion/diff workload must be benchmarked.

### Resource consumption

**No reliable benchmark found** that comparably measures GLPI Agent, OCS Agent and fleetd/osquery on the same Windows hardware, inventory categories and schedule. Individual issue logs and anecdotes are not a benchmark. Fleet/osquery exposes watchdog/resource controls and query statistics, reinforcing that cost depends on query design ([Fleet performance guide](https://fleetdm.com/guides/osquery-evented-tables-overview)).

Phase 0 must measure on low-end lab PCs:

- idle/scan peak RSS and CPU;
- scan p50/p95 duration;
- payload compressed/uncompressed size;
- disk writes/log growth;
- network retry behavior;
- effect of software inventory and EDID/WMI timeouts.

---

## K. Security Model

### Threats

- stolen/shared enrollment secret permits fake inventory submission;
- local administrator can tamper with agent, WMI output or identifiers;
- cloned agent state can impersonate another endpoint;
- replay of old payloads;
- API token leakage and over-privileged integration account;
- sensitive collection: usernames, software, IP/MAC, Windows product data, optionally processes/registry;
- parser/payload DoS and inventory floods;
- backend compromise changes baselines or hides incidents.

### MVP minimum

1. TLS 1.2+ with normal CA validation; prohibit `NO_SSL_CHECK` in production.
2. Per-device credential after one-time enrollment; short-lived/bootstrap secret only for enrollment. Prefer mTLS or signed requests when feasible.
3. Bind device credential to server-side endpoint identity; rotation/revocation and duplicate-ID quarantine.
4. Payload timestamp, nonce/request ID, hash and replay window.
5. Max payload size, schema allowlist, decompression limits, rate limits and safe parsers.
6. RBAC: viewer, inventory operator, incident reviewer, admin; organization/tenant scoping.
7. Immutable audit log for baseline acceptance, incident classification and manual relinking.
8. Encrypt secrets at rest; separate integration credentials; no direct DB exposure.
9. Minimize categories: do not collect processes, user files, registry keys or product keys unless justified.
10. Signed upstream installer verification and staged updates.

Inventory is **telemetry, not attestation**. A local administrator can spoof it. AssetGuard UI must label its source and confidence; QR/human verification provides an independent signal but is also not cryptographic proof.

---

## L. Licensing

| Project/component | License | Practical impact |
|---|---|---|
| OCS 2.x server/legacy Windows agent | GPL-2.0 family | Commercial use allowed; distributing modified binaries generally triggers source/license obligations for the modified GPL work |
| OCS 3 backend/agent | GPL-3.0 | Same separation principle; new code is GPL-3.0 |
| GLPI Agent | GPL-2.0-or-later | Run and communicate with it as a separate process; avoid copying/linking code into proprietary AssetGuard |
| GLPI core | GPL-3.0-or-later | Running as a separate service is the clean boundary; modifications distributed to customers must follow GPL |
| GLPI Inventory plugin | AGPL-3.0 | Network-use clause raises extra obligations for modifications; avoid making it part of AssetGuard unless needed |
| GLPI inventory format library | MIT | Schema/conversion library is permissive ([composer metadata](https://github.com/glpi-project/inventory_format/blob/main/composer.json)) |
| osquery | Apache-2.0 OR GPL-2.0-only | Apache choice is permissive and commercially friendly ([license](https://github.com/osquery/osquery/blob/master/LICENSE)) |
| Fleet free portion | Mostly MIT; paid code commercial | Verify file-level boundary; do not assume every repository path is MIT ([Fleet FAQ](https://github.com/fleetdm/fleet/blob/main/docs/Get%20started/FAQ.md)) |
| Snipe-IT | AGPL-3.0 | Separate service safest; modified network-served application can require source offer |

### Safe architecture

```text
Upstream GPL agent, unmodified executable
        │ HTTPS/JSON protocol boundary
        ▼
AssetGuard proprietary/open-source backend (independent codebase)
        │ optional REST boundary
        ▼
Unmodified GLPI/OCS sidecar service
```

Operational rules:

- distribute upstream installer separately with its license/notices and source offer/link as required;
- do not statically/dynamically link GPL agent/server code into AssetGuard;
- do not copy GLPI/OCS implementation code; use documented protocols and MIT schema where applicable;
- maintain SBOM and exact component/license versions;
- if modifying an agent, publish corresponding source and notices for that agent build;
- get counsel before closed-source redistribution/OEM packaging, especially around GPL/AGPL and installer bundling.

Mere use of a separate GPL service through HTTP normally does not make an independent client a derivative work, and ordinary SaaS use of GPL (unlike AGPL) usually does not itself trigger distribution source obligations. These are engineering risk boundaries, **not legal advice**.

---

## M. Risks

### Technical

- Direct GLPI Agent protocol may have undocumented negotiation/version coupling.
- Partial inventories can create false removals if treated as full snapshots.
- Collector upgrades can rename/normalize fields and generate mass diffs.
- GLPI API object model may not expose the raw fidelity needed for identity.

### Hardware identification

- SMBIOS/EDID values may be absent, generic, duplicated or malformed.
- USB/NVMe bridges and RAID controllers can obscure physical disk serials.
- Soldered RAM and integrated devices do not behave as movable components.
- GPU identity is generally model-level, not unit-level.

### Licensing

- Modified/bundled GPL agent distribution.
- Accidental use of AGPL plugin/server code in AssetGuard.
- Assuming repository-wide MIT for open-core Fleet.

### Deployment

- GPO/MSI failures, antivirus blocking, certificate rotation, proxy differences.
- Scan storms after mass boot/network return.
- Educational PCs often run without reliable connectivity or correct time.

### Security

- Agent telemetry spoofing, replay, cloned credentials.
- Excessive collection and personal-data exposure.
- Admin misuse of baseline acceptance/history editing.

### Scalability

- Installed software dominates payload/cardinality.
- Full JSONB snapshots grow quickly.
- Polling GLPI per asset becomes inefficient at thousands of devices.

### False positives

- monitor disconnected/docked;
- firmware update changes formatting;
- RAM serial was previously unreadable;
- disk exposed differently after driver/controller update;
- partial/failed scan interpreted as absence;
- motherboard replacement changes device UUID.

Mitigation: source completeness, confidence, consecutive-observation policies, maintenance windows, event deduplication, manual verification and replayable raw data.

---

## N. MVP Recommendation

### Demo scope

Only Windows desktops/laptops, one organization, one admin role, 10–30 endpoints.

Must demonstrate:

1. Register/link `Asset` and inventory number.
2. Receive first full inventory.
3. Display normalized components and accept baseline.
4. Remove/replace one RAM module or disk in lab hardware/VM fixture.
5. Receive next inventory.
6. Show evidence-backed `REMOVED` / `ADDED` event and one unresolved incident.
7. Classify as Planned Maintenance / Upgrade / Repair / Transfer / Authorized / Unknown / Investigation.
8. Show immutable history and current/baseline comparison.
9. Mark offline endpoint as `Requires Verification` after policy, never “missing/stolen”.

### Explicitly out of MVP

QR, mobile UI, 1C, network discovery, custom agent, AI, multi-tenant billing, automated theft claims, universal component movement and full ITSM/helpdesk.

### Success criteria

- ≥95% of pilot PCs yield usable device serial or UUID, with exceptions visible.
- Lab RAM/disk change detected with zero false removals from partial inventory.
- Repeated identical scan produces zero duplicate events.
- Raw payload can be renormalized to the same or intentionally versioned result.
- Offline/retry and cloned identifier scenarios have deterministic behavior.
- Agent scan overhead measured and acceptable on the lowest-spec pilot PC.

---

## O. Implementation Plan

### Phase 0 — Research / PoC (1–2 weeks)

- Test GLPI Agent on 5–10 representative Windows machines.
- Capture full and partial JSON inventories; validate exact fields and default values.
- Prove direct receiver protocol. In parallel, prove GLPI 11 API fallback.
- Measure scan CPU/RAM/duration/payload.
- Test reinstall, hostname change, motherboard/VM UUID change, cloned agent state.
- Build offline fixtures from sanitized inventories; no production application yet.
- Gate: choose direct ingestion or GLPI sidecar based on evidence.

### Phase 1 — MVP (3–6 weeks)

- Modular monolith + PostgreSQL.
- Asset/accounting model, raw inventory, canonical snapshots.
- Identity resolver v1 for device/RAM/disk.
- Diff engine with full-vs-partial safety and deduplication.
- Incident classification and asset timeline.
- Minimal web UI and installer/deployment guide.
- Automated tests from recorded fixtures.

### Phase 2 — Pilot (4–8 weeks)

- 100–1,000 PCs, GPO rollout rings.
- RBAC/audit, mTLS or signed device credentials, retention policies.
- Physical inventory session + QR.
- Excel import/export and reconciliation reports.
- Monitor false-positive rules and component movement candidates.
- Load, chaos/retry and upgrade testing.

### Phase 3 — Production

- HA ingress/workers/PostgreSQL backups and DR.
- Multi-organization isolation, SSO/AD integration.
- Agent update governance and certificate lifecycle.
- 1C adapter after customer-specific data contract.
- Reporting, SLA/observability, data retention and legal/privacy review.
- Re-evaluate OCS 3 stable and Fleet adapters; do not migrate without a measured advantage.

---

## Final Decision

**Go** for a narrow AssetGuard PoC, provided the product is positioned as continuous reconciliation and incident workflow, not generic inventory/ITSM.

**Foundation:** unmodified **GLPI Agent**.  
**Preferred ingestion:** direct versioned JSON receiver after Phase 0 proof.  
**Fallback:** unmodified **GLPI 11** sidecar + API adapter.  
**Own differentiating code:** raw evidence, canonical snapshots, confidence-aware identity, diff, incidents, expected/technical/physical reconciliation and history.  
**Do not select now:** OCS 3.0 RC, OCS 2.x as strategic backend, Fleet solely for inventory, or a custom Windows collector.

The fastest honest test is not “can we inventory a PC?”—GLPI/OCS already prove that. It is: **can AssetGuard turn imperfect hardware observations into a trustworthy, low-noise, auditable change workflow that organizations actually use?**
