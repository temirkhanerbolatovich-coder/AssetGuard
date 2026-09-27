# AssetGuard — актуальный полный чек-лист проекта

Дата актуализации: **27 сентября 2026 года**

Проверенная ветка: **актуальная `main`, синхронизированная с GitHub**

Production: **https://assetguard-temirkhan.duckdns.org**  
Версия схемы БД: **`0024_physical_asset_operations`**

Этот документ — единая точка правды о текущем состоянии AssetGuard. Статус «реализовано» означает, что функция присутствует в коде и покрыта автоматической либо выполненной ручной проверкой. Статус «частично» означает, что рабочий сценарий есть, но ещё не закрыты эксплуатационные, масштабные или продуктовые требования.

## Краткий итог

AssetGuard уже является работающим pilot MVP: школьный реестр, структура помещений, Windows Agent, техническая инвентаризация, baseline и инциденты, физические обходы, реальные перемещение/списание, Excel/PDF, QR, пользователи и доступы, локальный Vision, постоянный HTTPS-сервер и CI работают.

Для полноценного многопользовательского production-продукта в нескольких школах ещё нужны прежде всего испытание парка реальных ПК, политика хранения данных и безопасное обновление подписанного Agent.

Обозначения:

- ✅ реализовано и проверено;
- 🟡 реализовано частично или требует эксплуатационного завершения;
- ⛔ отсутствует.

## Реализовано и проверено

| Область | Статус | Что работает сейчас | Проверка |
| --- | --- | --- | --- |
| Backend и БД | ✅ | FastAPI, PostgreSQL 17, SQLAlchemy, Alembic; миграции до `0024` | Полный upgrade и rehearsal `0024 → 0023 → 0024` |
| Raw inventory | ✅ | Неизменяемый исходный payload, hash, idempotency, processing status | Integration tests и DB triggers |
| GLPI Agent transport | ✅ | Native GLPI Agent 1.19 `PROLOG → INVENTORY` и JSON bridge | Реальный Windows-PC и fixtures |
| Аппаратная инвентаризация | ✅ | CPU, RAM, накопители, GPU, motherboard, сеть, мониторы, BIOS/идентификаторы | Unit/integration tests |
| Endpoint identity | ✅ | Стабильные идентификаторы, hostname history, обнаружение конфликтов | Automated tests |
| Baseline и изменения | ✅ | Явное подтверждение эталона, сравнение «Было → Стало», защита PARTIAL inventory | Automated workflow |
| Технические инциденты | ✅ | Создание, классификация, закрытие, evidence и история | Integration и browser E2E |
| Реестр имущества | ✅ | Индивидуальный и групповой учёт, количество, единицы измерения, категории | API и UI tests |
| Иерархия школы | ✅ | Организация → корпус → этаж → кабинет, ответственные и единая карточка кабинета | API/UI workflow |
| Пользователи и сессии | ✅ | Именованные пользователи, роли, login/logout, отзыв сессий, смена пароля и отключение | Auth lifecycle tests |
| Права по локациям | ✅ для основных сценариев | Grants `VIEWER`/`EDITOR` на корпус, этаж или кабинет; API проверяет область доступа | Scoped-resource tests |
| Credentials устройств | ✅ | Отдельный username/secret на каждый Agent, one-time показ, hash в БД, revoke | API, UI и installer flow |
| Windows installer | ✅ для пилота | `AssetGuard-Agent-Setup-0.1.5.exe`, HTTPS server URL, уникальные credentials, Windows-служба с автозапуском | Установка и отправка inventory проверены на реальном ПК |
| Работа Agent в фоне | ✅ | GLPI Agent работает Windows-службой; остановка/изменение требует административных прав ОС | Реальная установка |
| Физический обход | ✅ | Полная сверка каждой позиции: на месте / отсутствует / повреждено, количество, комментарий и исполнитель | Integration и browser E2E |
| Физические инциденты | ✅ | Автоматическое создание из расхождения, проверка, ремонт, ложное срабатывание | Integration и browser E2E |
| Перемещение имущества | ✅ | Выбор целевого кабинета, целое или частичное перемещение групповой позиции, новый инвентарный номер, история | Integration test |
| Списание имущества | ✅ | Частичное уменьшение группового остатка либо полное `WRITTEN_OFF` | Integration test |
| PDF-акты операций | ✅ | Акт перемещения/списания с номером, количеством, маршрутом, основанием и исполнителем | Генерация и `%PDF` проверены |
| Excel import/export | ✅ | Предпросмотр всех строк, поиск, пагинация, create/update, исключение строк и подтверждение | Integration и browser E2E |
| PDF import/export | ✅ для поддерживаемых форм | Текстовые PDF и локальный OCR сканов; обязательный предпросмотр перед записью | Unit/integration tests на образцах |
| QR карточки | ✅ | QR открывает карточку конкретного актива по публичному URL | API test |
| Vision demo | ✅ локально | JPEG/PNG → Grounding DINO → bounding boxes/counts → baseline → повторный scan → `WARNING` | API workflow, demo images, отдельный real-model CI smoke |
| Связь Vision с реестром | ✅ на уровне scan | Проверка выбирает канонический кабинет и может быть связана с одним Asset | API/UI |
| Сетевые метрики Agent | ✅ базово | Опциональные ICMP availability, packet loss и average latency | Inventory fixture |
| Безопасность API | ✅ foundation | HTTPS, security headers, payload limits, app rate limiting, секреты вне Git, immutable evidence/history | CI и production config |
| Dependency scanning | ✅ | `pip check`, строгий `pip-audit`, Dependabot | GitHub Actions |
| Backup/restore tooling | ✅ Windows + server | AES-256-GCM backup, R2 upload/retention и isolated restore rehearsal; Windows/Linux AGBK1 совместимость | Windows tasks завершились с кодом `0`; server backup и restore rehearsal завершились `PASS` 2026-09-27 |
| Telegram monitoring | ✅ базовый production-контур | Каждые 5 минут: readiness, Compose services, disk, backup age/job failures, offline Agent, failed ingest и identity conflicts; дедупликация и повтор через 4 часа | Telegram принял test alert, второй запуск был подавлен, normal run прошёл 2026-09-27 |
| Постоянный deployment | ✅ | Oracle Cloud Always Free, Docker Compose, Caddy, DuckDNS, TLS, restart policy | Public health/readiness |
| CI | ✅ | PostgreSQL tests, browser E2E, dependency audit, JS/PowerShell checks, Compose validation | GitHub Actions |

Последняя подтверждённая локальная проверка: **все 45 backend-тестов пройдены единым запуском**: 43 unit/integration и 2 browser E2E. Disposable PostgreSQL очищается перед каждым тестом, а in-memory rate limiter не переносит состояние между сценариями.

## Реализовано частично

| Область | Что уже есть | Чего не хватает до полного production |
| --- | --- | --- |
| Multi-tenant | Organization scope есть у пользователей, credentials, assets, endpoints, inventory и Vision; исполняемая allow/deny-матрица покрывает все 57 защищённых admin operations | Отдельная роль tenant administrator и тест двух реальных школ |
| Мониторинг | Постоянный systemd monitor проверяет API, Compose services, диск, возраст/ошибки backup, ingest и Agent last-seen; доставка, дедупликация и четырёхчасовой repeat Telegram-alert приняты | Dashboard наблюдаемости и формальная on-call escalation |
| Backup | Зашифрованные копии, Cloudflare R2, 14 дней локально / 30 дней off-site; Windows и постоянные Linux timers работают; server restore rehearsal `PASS` 2026-09-27 | Наблюдать следующий автоматический daily/weekly цикл; backup пока охватывает PostgreSQL, но не Vision volume |
| Vision production | Полный локальный photo workflow и настоящий model smoke в CI | Oracle Free VM не тянет ML runtime; нужны отдельный inference host/GPU либо более мощный сервер, object storage и accuracy evaluation |
| Хранение данных | Raw evidence и audit защищены от изменения; Vision лежит в persistent volume | Утверждённые сроки хранения, автоматическая очистка/архив Vision, экспорт и процедура удаления по политике |
| Installer lifecycle | Установка службы и первичное подключение работают | Code signing, SmartScreen reputation, versioned update/rollback и массовое развёртывание |
| Agent lifecycle | Уникальные credentials и revoke работают | Self-service re-enrolment, безопасное перевыпускание после переустановки, отключение legacy shared secret |
| Проверка парка ПК | Один реальный Windows-PC проверен | Несколько моделей ПК, cold boot, offline queue/retry, reimage, смена железа, service recovery и обновление |
| PDF import | Типовые таблицы и OCR поддерживаются | Мастер ручного сопоставления нестандартных колонок, список ошибок, объединение дубликатов, больше реальных ведомостей РК |
| Отчётность | Реестр, PDF/Excel, карточка кабинета, история и акты операций | Сводки по школе/ответственным/категориям/состояниям, журнал операций за период, scheduled reports |
| QR-инвентаризация | QR актива открывает карточку | QR кабинета, мобильный режим обхода, offline/PWA и сканирование камерой телефона |
| Security hardening | Dependency audit, автоматический secret scan всей Git-истории, pre-commit hook, rate limit приложения, TLS, роли, append-only | Proxy-level rate limiting, SAST, container scan, SBOM, MFA/SSO и внешний pentest |
| Admin audit | Инциденты, baseline, активы и операции оставляют history | Единый журнал всех административных действий: пользователи, grants, credential revoke, imports и настройки |
| Operations | Production Compose и restart policy работают | Staging, blue/green или rollback automation, release tags, SLA/runbook инцидентов |
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

1. **Fleet test:** установить Agent минимум на 3–5 разных ПК и проверить перезагрузку, отсутствие сети, повторную доставку, смену железа, revoke и восстановление службы.
2. **Data governance:** утвердить, какие данные собираются, кто имеет доступ, где они хранятся и когда удаляются; отдельно определить срок жизни Vision-фотографий.
3. **Release безопасности Agent:** подписать installer, зафиксировать SHA-256 и описать обновление/откат.

### P1 — следующий продуктовый релиз

1. Единый admin audit log и экран аудита.
2. Сводные отчёты школы и scheduled PDF/Excel reports.
3. QR кабинета и мобильный/PWA-обход.
4. Mapping wizard нестандартных Excel/PDF колонок.
5. Self-service re-enrolment и управляемое обновление Agent.
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
- оформить rollback и аварийный runbook.

Критерий готовности: тестово удалить disposable окружение, восстановить его только из внешней копии и получить автоматическое уведомление при намеренно остановленном API.

### Этап 2. Доказать безопасность нескольких школ

Результат: пользователь одной организации не может получить данные другой ни одним API-запросом.

- [x] составить исполняемую route/access matrix для всех 57 защищённых admin operations;
- добавить negative tests для foreign tenant и чужой локации;
- выделить полномочия tenant administrator;
- внедрить полный admin audit;
- отключить legacy shared credentials после миграции устройств.

Критерий готовности: CI автоматически проверяет все tenant/location boundaries, включая exports, images, history, credentials и операции имущества.

### Этап 3. Подготовить управляемый парк Agent

Результат: Agent можно безопасно массово установить, обновить, отозвать и восстановить.

- провести fleet test на 3–5 ПК;
- реализовать re-enrolment и version reporting;
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
