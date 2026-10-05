# AssetGuard — актуальный полный чек-лист проекта

Дата актуализации: **5 октября 2026 года**

Ветка учёта: **`main`**

Production: **https://assetguard-temirkhan.duckdns.org**  
Версия схемы репозитория: **`0026_telegram_notifications`**

Предыдущая приёмка UI/UX 2026-10-05: **этапы UI/UX 1–4 и автоматическая часть этапа 5 приняты на production**, application commit `0f67995`. **109 backend + 16 browser E2E**, CI, Secret scan и dependency audit прошли. Контраст/фокус/dialogs/reflow, реестр 216/1000 assets и scoped hardware summaries проверены. На production SQL assets/endpoints **65/105 → 4/4**, ответы совпали; cold workspace в двух samples около 2.4 → 1.9 s, warm результат нестабилен. Schema `0026`, **63 защищённые операции**; read-only UI/API и свежий R2 restore прошли. [Оптимизация](../../outputs/assetguard-registry-performance-2026-10-05.md), [UI этап 5](../../outputs/assetguard-ui-stage5-2026-10-05.md), [открытая ручная приёмка](../testing/ui-acceptance.md). Полная WCAG/usability и полевые performance budgets пока не приняты.

Текущая рабочая точка — **Agent 0.1.8 принят на одном реальном PC, серверный application `fa22015` развёрнут и проверен**. Независимый локальный сбор примерно каждые 5–6 минут плюс scheduler delay, offline FIFO, bounded randomized delivery; старым Agent PROLOG 360 s при следующем контакте. **122 backend + 16 browser E2E**, GitHub CI и production API/auth/projection прошли. Реальные автоматические интервалы 304–366 s; controlled offline/lost ACK: 4 HTTPS attempts → 3 raw/snapshots у прежнего endpoint. [Контракт](../features/agent-continuous-inventory.md), [протокол](../../outputs/assetguard-agent-reliability-2026-10-05.md). Финальный readiness helper/EXE исправляет локализованный SYSTEM; его повторная установка на этом PC отменена в UAC, исходный отчёт 13/14 по этому единственному ложному отказу. Fleet, физический offline/reboot и массовое обновление не закрыты.

Предыдущие UI/UX этапы: [1 — вход и каркас](../../outputs/assetguard-ui-stage1-2026-10-05.md) (`d8f6a63`), [2 — реестр и инциденты](../../outputs/assetguard-ui-stage2-2026-10-05.md) (`c254125`), [3 — кабинеты, обход и импорт](../../outputs/assetguard-ui-stage3-2026-10-05.md) (`2ae4b01`), [4 — Agent и администрирование](../../outputs/assetguard-ui-stage4-2026-10-05.md) (`45d739b`). Следующий UI/UX шаг: настоящий zoom 200%/400%, screen reader/mobile, representative performance и usability с 3–5 сотрудниками. Assets/endpoints пока загружаются целиком; hardware summaries читаются пакетно по доступным ПК, история ограничена 50 snapshots на ПК. API exactly-once записи не заявляется: при потере ответа сначала проверяется состояние/история.

Telegram ранее принят на `0b90607`, schema `0026`; после UI-релиза очередь и штатное подавление повтора проверены вновь, таймеры активны. [Приёмка Telegram](../../outputs/assetguard-telegram-2026-10-05.md), [функция и настройка](../features/telegram-notifications.md). Live при приёмке Agent 09:57 Asia/Qyzylorda: **11 PC, 5 online / 6 stale**, failed ingest 0, pending/retrying 0. Fleet acceptance, подпись/публикация installer 0.1.8 и Vision production остаются самостоятельными задачами.

Последняя проверенная production/R2 restore revision: **`0026_telegram_notifications`**, 2026-10-05 по времени клиента, **216 assets / 11 endpoints**.

Предыдущий этап: **стабилизация принята на production 2026-10-04**, application commit `93ff8ed`, schema `0025`. Push/manual CI прошли, включая реальную модель; backup/restore и recovery проверены. [Исторический протокол](../../outputs/assetguard-release-2026-10-04.md). Windows installer `0.1.7` пока не опубликован.

Этот документ — единая точка правды о текущем состоянии AssetGuard. Статус «реализовано» означает, что функция присутствует в коде и покрыта автоматической либо выполненной ручной проверкой. Статус «частично» означает, что рабочий сценарий есть, но ещё не закрыты эксплуатационные, масштабные или продуктовые требования.

## Краткий итог

AssetGuard является работающим pilot MVP: школьный реестр, структура помещений, Windows Agent, техническая инвентаризация, baseline и инциденты, физические обходы, перемещение/списание, Excel/PDF, QR, пользователи и доступы, локальный Vision и постоянный HTTPS-сервер реализованы. Исправления стабилизации опубликованы и развёрнуты из проверенного application commit; CI и серверная приёмка прошли. Изменения документов после выкладки не меняют этот application image.

Для полноценного многопользовательского production-продукта в нескольких школах ещё нужны прежде всего испытание парка реальных ПК, политика хранения данных и безопасное обновление подписанного Agent.

Обозначения:

- ✅ реализовано и проверено;
- 🟡 реализовано частично или требует эксплуатационного завершения;
- ⛔ отсутствует.

## Реализовано и проверено

| Область | Статус | Что работает сейчас | Проверка |
| --- | --- | --- | --- |
| Backend и БД | ✅ | FastAPI, PostgreSQL 17, SQLAlchemy, Alembic; production migrations до `0026` | CI; isolated upgrade/downgrade/re-upgrade; actual production revision и свежий R2 restore `0026` |
| Raw inventory | ✅ | Неизменяемый исходный payload, hash, idempotency, processing status | Integration tests и DB triggers |
| GLPI Agent transport | ✅ | Native GLPI Agent 1.19/1.20 `PROLOG → INVENTORY` и JSON bridge | Два реальных Windows-PC и fixtures |
| Аппаратная инвентаризация | ✅ | CPU, RAM, накопители, GPU, motherboard, сеть, мониторы, BIOS/идентификаторы | Unit/integration tests |
| Endpoint identity | ✅ | Стабильные идентификаторы, hostname history, обнаружение конфликтов | Automated tests |
| Baseline и изменения | ✅ | Явное подтверждение эталона, сравнение «Было → Стало», защита PARTIAL inventory | Automated workflow |
| Технические инциденты | ✅ | Создание, классификация, закрытие, evidence и история | Integration и browser E2E |
| Реестр имущества | ✅ | Индивидуальный и групповой учёт, количество, единицы измерения, категории | API и UI tests |
| Иерархия школы | ✅ | Организация → корпус → этаж → кабинет, ответственные и единая карточка кабинета | API/UI workflow |
| Пользователи и сессии | ✅ | Именованные пользователи, роли, login/logout, отзыв сессий, смена пароля и отключение | Auth lifecycle tests |
| Права по локациям | ✅ для основных сценариев | Grants `VIEWER`/`EDITOR` на корпус, этаж или кабинет; API проверяет область доступа | Scoped-resource tests |
| Credentials устройств | ✅ | Отдельный username/secret на каждый Agent, one-time показ, hash в БД, revoke | API, UI и installer flow |
| Windows installer | 🟡 0.1.8 candidate | Опубликован 0.1.6; новый 0.1.8 сохраняет version reporting/re-enrolment и добавляет offline delivery, обновление с сохранением ключа | Полная fleet-приёмка нового задания, code signing и публикация ещё не закрыты |
| Работа Agent в фоне | ✅ на одном PC / 🟡 fleet | 0.1.8: независимый сбор, SYSTEM task, offline FIFO и randomized delivery; native daemon отключён | 138 tests, реальные автоматические циклы, 3 controlled offline captures → 4 HTTPS attempts → 3 raw/snapshots у прежнего endpoint; физический network/reboot fleet открыт |
| Физический обход | ✅ | Полная сверка каждой позиции: на месте / отсутствует / повреждено, количество, комментарий и исполнитель | Integration и browser E2E |
| Физические инциденты | ✅ | Создание из расхождения, единый центр, исходное evidence, проверка, ремонт/операции и решения | Tenant/location integration и browser E2E |
| Перемещение имущества | ✅ | Выбор целевого кабинета, целое или частичное перемещение групповой позиции, новый инвентарный номер, история | Integration test |
| Списание имущества | ✅ | Частичное уменьшение группового остатка либо полное `WRITTEN_OFF` | Integration test |
| PDF-акты операций | ✅ | Акт перемещения/списания с номером, количеством, маршрутом, основанием и исполнителем | Генерация и `%PDF` проверены |
| Excel import/export | ✅ для поддерживаемых форм | Tenant-safe preview/create/update; quantity/unit/tracking_mode, сохранение учёта после актов и старых файлов без новых колонок; код развёрнут | PostgreSQL integration и browser E2E в CI; реальные записи production для теста не изменялись |
| PDF import/export | ✅ для поддерживаемых форм | Текстовые PDF и локальный OCR сканов; обязательный предпросмотр перед записью | Unit/integration tests на образцах |
| QR карточки | ✅ | QR открывает карточку конкретного актива по публичному URL | API test |
| Vision demo | ✅ локально | JPEG/PNG → Grounding DINO → bounding boxes/counts → baseline → повторный scan → `WARNING` | API workflow, demo images, отдельный real-model CI smoke |
| Связь Vision с реестром | ✅ на уровне scan | Проверка выбирает канонический кабинет и может быть связана с одним Asset | API/UI |
| Сетевые метрики Agent | ✅ базово | Опциональные ICMP availability, packet loss и average latency | Inventory fixture |
| Безопасность API | ✅ foundation | HTTPS, security headers, payload limits, app rate limiting, секреты вне Git, immutable evidence/history | CI и production config |
| Dependency scanning | ✅ | `pip check`, строгий `pip-audit`, Dependabot | GitHub Actions |
| Backup/restore tooling | ✅ Windows + server | AES-256-GCM backup, R2 upload/retention и isolated restore rehearsal; Windows/Linux AGBK1 совместимость | Windows tasks: код `0` 2026-09-27; server daily/weekly cycle и свежие pre/post-deployment restore `PASS` 2026-10-04, последний на `0026` (2026-10-05 по времени клиента) |
| Telegram | ✅ production pilot | Новые технические/физические инциденты через durable queue раз в минуту; проблемы Agent/сервера раз в 5 минут; retry/429 и штатная дедупликация | 2026-10-05: Telegram acceptance, подтверждение пользователя, повторный и автоматический запуск без дубля; tenant/location/retry tests |
| Постоянный deployment | ✅ | Oracle Cloud Always Free, Docker Compose, Caddy, DuckDNS, TLS, restart policy | Public health/readiness |
| CI | ✅ | PostgreSQL tests, browser E2E, dependency audit, JS/PowerShell/Linux checks, Compose validation и real-model smoke | Application push `37246722604` success на `2ae4b01`; прежний manual model smoke `37223446315` на `93ff8ed` |

Проверка стабилизации 2026-10-04 локально и в GitHub CI: **80 unit/integration и 2 browser E2E**. Disposable PostgreSQL 17 применяет все 25 migrations до `0025`, очищается перед каждым тестом; rate limiter также сбрасывается. Реальная Grounding DINO прошла offline smoke и manual GitHub model download/inference: **23 detections**. Это runtime smoke, а не quality benchmark. [Push CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223402190) и [manual CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223446315) на `93ff8ed` завершились success; transient secret-scan API rate-limit устранён успешным повтором без bypass.

Production read-only counts: **216 assets, 11 endpoints, 51 raw inventories, 51 snapshots, 17 credentials, 0 re-enrolment requests**. Operations: 1 online, 10 stale, 0 offline/conflicts/failed ingests. Отсутствие свежей телеметрии 10 ПК остаётся предметом fleet acceptance; для прохождения приёмки эти данные не исправлялись вручную.

Закрыто в стабилизации и выкладке:

- [x] обычный Windows venv startup и disposable PostgreSQL test environment;
- [x] Agent endpoint/tenant checks до доменных изменений, включая duplicates, смешанные identifiers, unowned endpoint и уже занятый credential;
- [x] Excel/PDF tenant fallback для preview/create/update без записи в чужую организацию;
- [x] age-based stale counters и monitor dedup/recovery/retry с подставной доставкой;
- [x] structured import/export количества, единицы и режима, сохранение остатков после актов;
- [x] обязательные env settings smoke job и локальный real-model smoke без изменения Vision logic;
- [x] публикация проверенных изменений и свежий GitHub CI, включая manual real-model smoke;
- [x] свежие pre/post-deployment R2 backup/restore, upgrade/recovery rehearsal, rollout API/UI/schema и controlled production alert/dedup;
- [ ] fleet acceptance на 3–5 реальных ПК, включая installer `0.1.8`.

## Реализовано частично

| Область | Что уже есть | Чего не хватает до полного production |
| --- | --- | --- |
| Multi-tenant | Organization scope и scoped ADMIN; матрица 63 admin operations; negative tests для native Agent ingestion и Excel/PDF import | Явные platform/onboarding полномочия, отказ от legacy global fallback и приёмка двух реальных школ |
| Мониторинг | Постоянный systemd monitor проверяет API, Compose services, диск, возраст/ошибки backup, ingest и Agent last-seen; доставка, дедупликация и четырёхчасовой repeat Telegram-alert приняты | Журнал индивидуальных переходов Agent и формальная on-call escalation |
| Backup | Зашифрованные копии, Cloudflare R2, 14 дней локально / 30 дней off-site; Windows и Linux timers; свежий restore `0026` прошёл 2026-10-05 по времени клиента | Backup пока охватывает PostgreSQL, но не Vision volume; длительное наблюдение за регулярными циклами |
| Vision production | Полный локальный photo workflow и настоящий model smoke в CI | Oracle Free VM не тянет ML runtime; нужны отдельный inference host/GPU либо более мощный сервер, object storage и accuracy evaluation |
| Хранение данных | Raw evidence и audit защищены от изменения; Vision лежит в persistent volume | Утверждённые сроки хранения, автоматическая очистка/архив Vision, экспорт и процедура удаления по политике |
| Installer lifecycle | 0.1.8 установлен на одном PC: SYSTEM task, offline queue, version reporting, lifecycle log и обновление с сохранением текущего ключа; финальный readiness helper исправляет SYSTEM locale | Code signing, финальная readiness/fleet acceptance, rollback и массовое развёртывание |
| Agent lifecycle | Уникальные credentials, revoke и подтверждаемое re-enrolment после переустановки работают; прежний ключ автоматически отзывается | Управляемое обновление/rollback и отключение legacy shared secret |
| Проверка парка ПК | Два реальных Windows-PC проверили transport 1.19/1.20; добавлен единый secret-free JSON-протокол fleet test | Минимум три полных цикла: cold boot, offline queue/retry, reimage, смена железа, service recovery и обновление |
| PDF import | Типовые таблицы и OCR поддерживаются | Мастер ручного сопоставления нестандартных колонок, список ошибок, объединение дубликатов, больше реальных ведомостей РК |
| Отчётность | Реестр, PDF/Excel, карточка кабинета, история и акты операций | Сводки по школе/ответственным/категориям/состояниям, журнал операций за период, scheduled reports |
| QR-инвентаризация | QR актива открывает карточку | QR кабинета, мобильный режим обхода, offline/PWA и сканирование камерой телефона |
| Security hardening | Dependency audit, автоматический secret scan всей Git-истории, pre-commit hook, rate limit приложения, TLS, роли, append-only | Proxy-level rate limiting, SAST, container scan, SBOM, MFA/SSO и внешний pentest |
| Admin audit | Инциденты, baseline, активы и операции оставляют history | Единый журнал всех административных действий: пользователи, grants, credential revoke, imports и настройки |
| Operations | Production Compose/restart policy; документирован и испытан recovery на pre-release копии; старый image сохранён | Staging, production failover, rollback automation с учётом новых re-enrolment data, release tags и SLA |
| UX | Основные сценарии и адаптивность реализованы | Модерируемый тест с сотрудниками школы, accessibility audit и устранение найденных проблем |

## Пока не реализовано

- ⛔ MFA, SSO и интеграция с Active Directory.
- ⛔ Интеграции с 1С, helpdesk и внешними бухгалтерскими системами.
- ⛔ RTSP-камеры, расписание съёмки, multi-frame confirmation и потоковое видео.
- ⛔ Надёжное сопоставление каждой Vision detection с конкретным инвентарным объектом или endpoint.
- ⛔ Production object storage для фотографий Vision.
- ⛔ Мобильное приложение/PWA и QR-запуск обхода кабинета.
- ⛔ Автоматическое обновление и откат Windows Agent.
- ⛔ Подписанный сертификатом установщик.
- ⛔ Полноценный сервер метрик уровня Prometheus/Grafana либо эквивалент.
- ⛔ Нагрузочные тесты на целевое количество школ, пользователей и endpoints.
- ⛔ SAST, container image scan и SBOM.
- ⛔ Юридически утверждённая политика обработки школьных данных и фотографий помещений.

## Известные границы, которые не являются ошибками

- Production Oracle VM обслуживает API, PostgreSQL и Agent ingest, но не запускает тяжёлую Grounding DINO-модель. Vision для демонстрации запускается локально.
- `WARNING`, offline Agent или отсутствие telemetry означает «нужна проверка», а не автоматически «кража».
- Agent не читает пользовательские файлы, историю браузера и содержимое сетевого трафика.
- Сетевой профиль не измеряет скорость канала и jitter; сейчас доступны только ICMP availability/loss/latency.
- OCR не гарантирует точность. Ни одна распознанная строка не должна применяться без предпросмотра человеком.

## Приоритетные задачи

### P0 — обязательны до пилота с реальной школой

Publication/CI/server/backup/migration/controlled alert для application `93ff8ed` закрыты 2026-10-04; это не закрывает испытания реального парка и границы многопользовательского production.

1. **Fleet test:** установить Agent минимум на 3–5 разных ПК и проверить перезагрузку, отсутствие сети, повторную доставку, смену железа, revoke, re-enrolment и восстановление службы; проверить оставшиеся stale endpoints (6 на снимке приёмки).
2. **Data governance:** утвердить состав/доступ/хранение/удаление данных, включая Vision-фотографии.
3. **Release безопасности Agent:** подписать installer, зафиксировать SHA-256 и испытать обновление/откат.

### P1 — следующий продуктовый релиз

1. Единый admin audit log и экран аудита.
2. Сводные отчёты школы и scheduled PDF/Excel reports.
3. QR кабинета и мобильный/PWA-обход.
4. Mapping wizard нестандартных Excel/PDF колонок.
5. Управляемое обновление и rollback Agent.
6. Staging, release tags и автоматизированный rollback.
7. MFA либо SSO/AD для администраторов.

### P2 — масштабирование и Vision production

1. Отдельный Vision inference service и object storage.
2. Evaluation dataset по реальным кабинетам, quality thresholds и human confirmation.
3. RTSP/multi-frame pipeline.
4. Сопоставление detections с Asset/endpoint.
5. Интеграции с 1С, AD и helpdesk.
6. Нагрузочное тестирование и capacity plan.

## План реализации по этапам

### Этап 1. Закрыть эксплуатационные риски

Результат: потеря сервера не приводит к потере данных, а ответственный узнаёт о сбое автоматически.

- [x] повторно авторизовать off-site remote и подтвердить ручной encrypted upload;
- [x] восстановить свежий off-site backup в изолированную БД и сохранить протокол проверки;
- [x] запустить Windows daily backup и weekly rehearsal через Task Scheduler; обе задачи завершились с кодом `0` 2026-09-27;
- [x] установить server daily backup, weekly restore rehearsal и 5-minute monitor timers;
- [x] выполнить server backup в R2 и isolated restore: `0024`, `assets=211`, `endpoints=1`, `PASS` 2026-09-27;
- [x] добавить alert по возрасту копии и failed backup/restore jobs;
- [x] подтвердить test alert: Telegram accepted, повторный запуск deduplicated, normal run healthy; неизменившаяся проблема повторяется через 4 часа;
- [x] оформить recovery runbook с ограничениями downgrade `0025` и проверить прежний/новый API на изолированной копии;
- [x] повторить backup/restore и Telegram acceptance/dedup после выкладки 2026-10-04; actual schema `0025`, assets=216, endpoints=11;
- [ ] испытать настоящий failover/сбой API в staging; тестовое сообщение не является испытанием аварии production.

Критерий готовности: тестово удалить disposable окружение, восстановить его только из внешней копии и получить автоматическое уведомление при намеренно остановленном API.

### Этап 2. Доказать безопасность нескольких школ

Результат: пользователь одной организации не может получить данные другой ни одним API-запросом.

- [x] составить исполняемую route/access matrix для всех 63 защищённых admin operations;
- [x] добавить negative tests для foreign tenant/локации, native ingestion и Excel/PDF imports;
- уточнить platform/onboarding полномочия с учётом существующего tenant-scoped ADMIN;
- внедрить полный admin audit;
- отключить legacy shared credentials после миграции устройств.

Критерий готовности: CI автоматически проверяет все tenant/location boundaries, включая exports, images, history, credentials и операции имущества.

### Этап 3. Подготовить управляемый парк Agent

Результат: Agent можно безопасно массово установить, обновить, отозвать и восстановить.

- провести fleet test на 3–5 ПК;
- проверить re-enrolment и version reporting на 3–5 реальных ПК;
- добавить подписанный installer;
- создать update/rollback workflow;
- проверить offline retry и восстановление после reboot/service failure.

Критерий готовности: все тестовые ПК переживают перезагрузку и потерю сети, а обновление не требует ручного редактирования конфигурации.

### Этап 4. Завершить продуктовый учёт

Результат: школа выполняет полный цикл без технического специалиста.

- сводные отчёты и фильтры операций;
- QR кабинета и mobile-first обход;
- mapping wizard для импортов;
- улучшение доступности и UX по результатам тестов пользователей;
- интеграционные контракты 1С/helpdesk.

Критерий готовности: сотрудник школы самостоятельно импортирует ведомость, проводит обход, разбирает расхождение, перемещает/списывает имущество и выгружает отчёт.

### Этап 5. Вывести Vision в production

Результат: Vision становится устойчивым источником наблюдений, а не только демонстрацией.

- собрать и разметить evaluation dataset;
- выбрать inference infrastructure;
- вынести изображения в object storage и включить retention;
- добавить quality gate, несколько кадров и human confirmation;
- затем подключать камеры/RTSP и mapping к активам.

Критерий готовности: измерены precision/recall по выбранным классам и условиям кабинетов, а ложное срабатывание не создаёт автоматического обвинительного вывода.

## Что показывать на демонстрации сейчас

1. Открыть публичный Dashboard и структуру школы.
2. Показать кабинет, категории имущества и физический обход.
3. Зафиксировать повреждение/отсутствие и показать автоматически созданный инцидент.
4. Выполнить перемещение или списание и скачать PDF-акт.
5. Открыть компьютер с реальными данными Agent, baseline и историей.
6. Локально показать Vision: baseline-фото → изменённое фото → bounding boxes и `WARNING`.
7. Завершить архитектурой: Agent, Vision и физический обход — независимые источники, объединённые в одном реестре и журнале решений.

## Правило актуализации

После каждого законченного этапа необходимо:

1. обновить этот чек-лист и профильные документы;
2. добавить или изменить автоматический тест;
3. выполнить миграционный rehearsal при изменении схемы;
4. дождаться успешного GitHub Actions CI;
5. развернуть production и проверить `/health`, `/health/ready`, версию миграции и публичный UI.
