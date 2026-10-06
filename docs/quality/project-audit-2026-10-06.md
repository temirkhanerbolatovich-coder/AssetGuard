# AssetGuard — аудит проекта и документации, 6 октября 2026

Дата: **2026-10-06, Asia/Qyzylorda (UTC+5)**. Исходный Git HEAD: `dca5a8672b21762d786e25054665c8eccbab9a53`, branch `main`. Объём: code/config/tests/docs, история связанных чатов, GitHub и read-only production. Изменения аудита ограничены документацией.

## Результат

После документационного аудита и просмотра сайта локально исправлены три UI/API-ошибки: согласованная свежесть Agent, разделение неподключённых компьютеров/ожидания первого отчёта и поддержка XML-представления версии 1.20. Новый полный прогон: **170 passed**; [отдельный протокол](../../outputs/assetguard-agent-status-fixes-2026-10-06/report.md). Это последующий этап: исходные инвентаризация/145 tests ниже сохраняют дату и объём аудита, production application остаётся последней подтверждённой `f4f56e7` до отдельной выкладки.

**AssetGuard — работающий pilot MVP.** Реализованы реестр, hierarchy/grants, техническая инвентаризация, explicit baseline, technical/physical incidents и решения, imports/exports, QR-обход, Ledger, Telegram и PostgreSQL backup/restore. Последняя application acceptance — `f4f56e7` от 6 октября; server docs checkout — `dca5a86`. Массовый multi-school rollout остаётся за gates fleet/signing/governance/tenant onboarding/staging/manual UI acceptance.

Основное обнаруженное расхождение — документация отставала от нескольких уже принятых релизов. Главный README и checklist смешивали текущие и исторические SHA/счётчики; QR был одновременно завершён и запланирован, часть Agent/UX/deployment инструкций описывала старое поведение. Эти расхождения исправлены. [Актуальный checklist](../product/current-project-checklist.md) — точка продолжения.

## Охват и метод

На входе: **428 tracked files, 86 Markdown-файлов, 6485 Markdown lines**. Состав: backend 137, frontend 10, docs 59, scripts 48, infra 10, installer 1, demo 3, outputs 149; остальные 11 — корневые/config files. Все tracked файлы инвентаризированы с размером и SHA-256; UTF-8 text читается без decode errors. [Полный inventory](../../outputs/assetguard-documentation-audit-2026-10-06/file-inventory.md).

Проверены composition root, HTTP routes и guards, настройки, migrations/triggers, raw/normalization/baseline/incident flows, notifications/worker, imports и accounting precedence, local Agent/task/queue, frontend contracts, deployment/backup/monitor scripts, fixtures и CI. Автоматические проверки дополняют просмотр критичных paths; inventory binary artifacts фиксирует наличие/размер/hash, без повторной генерации исторических медиа.

Каждый из 86 исходных Markdown-файлов отнесён к current guide, historical record, demo/reference или ADR/template. В 77 документах актуализированы содержание и/или указатель на текущее состояние; восемь принятых ADR и один ADR template сохранены. Добавлены четыре Markdown-документа: этот аудит, полный API reference, documentation register и file inventory. Итого в репозитории **90 Markdown-документов** после аудита. [Реестр и действие по каждому документу](../../outputs/assetguard-documentation-audit-2026-10-06/documentation-register.md).

`.env`, runtime `.local`, queues, XML, secrets и прочие ignored данные не публикуются. Четыре исходных untracked reference PNG, installer outputs, пользовательские `tmp/` и `acl-probe.txt` сохранены. Временные audit helpers находятся в ignored `tmp`; отдельный тестовый PostgreSQL создан только для этого аудита и удалён после проверок.

## Сверка GitHub и production

| Проверка | Результат и источник |
| --- | --- |
| Local/GitHub/server checkout | `dca5a8672b21762d786e25054665c8eccbab9a53`; GitHub branch API, local Git, read-only SSH |
| Repository | Public, default `main`; branch protected=false, отдельного LICENSE нет |
| Последний published installer | `v0.1.6`, prerelease, 2026-09-27; 0.1.8 отсутствует в Releases |
| Open dependency PRs | [#7 SQLAlchemy](https://github.com/temirkhanerbolatovich-coder/AssetGuard/pull/7), [#8 ReportLab](https://github.com/temirkhanerbolatovich-coder/AssetGuard/pull/8); в этом аудите не объединялись |
| Application CI | [`37433147495`](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37433147495), `f4f56e7`, success |
| Documentation CI | [`37435743838`](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37435743838), `dca5a86`, success |
| Production topology | Oracle Cloud VM / Docker Compose + Caddy; отдельного Render-контура нет в проверенном проекте |
| Running application image | `sha256:29062bad2c906e1b80afea322d20ee0ef3fb10a1778a0cdf7b60e9a6082a1fd3`, accepted `f4f56e7` |
| Schema | Server `0026_telegram_notifications (head)`; все 26 migrations в tests |
| Public HTTP | `/`, `/health`, `/health/ready`: 200; `/admin/endpoints` без token: 401; GET `/glpi-agent`: 404 |
| Public API | OpenAPI matches local: 73 operations, 64 protected admin; [полный reference](../api/route-reference.md) |
| Frontend | Public и container HTML/JS/CSS совпадают с Git application `f4f56e7` |
| Operational scripts | Четыре установленных monitor/notifications/backup/restore scripts побайтно соответствуют server checkout |
| Timers/jobs | Четыре timers active, failed units отсутствуют; последние services success, ExecMainStatus=0 |

UI SHA-256:

| Файл | SHA-256 |
| --- | --- |
| `index.html` | `dbecddfa408e51da98629b6a617adba8246c1c3a42235ea08891be34e15a381b` |
| `app.js` | `dae84b5b51c43dd7831a50cdccff83abe75f0af86bc5bc1c875c0c103301574c` |
| `styles.css` | `b2b84e9e9f6187bbc245ffbfbb87926f57934613a7ecf68dbd0d3d30cacd95c4` |

API/package version всё ещё `0.1.0`; это не SHA релиза и не версия installer. Health/readiness подтверждают process/DB, а schema/image/source проверялись отдельно.

## Read-only серверный срез

SQL прочитан **2026-10-06 12:29:16 UTC / 17:29:16 UTC+5**:

- assets **220**, managed endpoints **11**;
- raw inventories **389**, hardware snapshots **389**;
- computed Agent freshness: **6 ONLINE / 5 STALE**, 0 IDENTITY_CONFLICT;
- failed ingest **0**;
- Telegram **3 SENT**, PENDING на этом срезе отсутствует.

Числа меняются при работе Agent. Stale PC требуют проверки на месте; состояние online не является выполненной reboot/offline/fleet приёмкой. SENT означает acceptance сервиса, а не прочтение человеком.

Server backup status: `assetguard-production-20261006-075950.sql.agbackup`. Journal **08:01:18 UTC / 13:01:18 UTC+5** подтверждает isolated restore PASS: schema `0026`, assets=220, endpoints=11; restore service завершился success/0 в 08:01:26 UTC. Новый backup, restore или Telegram test в этом аудите не запускались; проверялись существующие status/journal/jobs. PostgreSQL backup не содержит Vision images.

Расписание в текущем systemd: следующий backup 2026-10-07 **07:00 UTC+5**, rehearsal 2026-10-11 **08:00 UTC+5** (units: 02:00/03:00 UTC). Отсутствие нового прогона не подменяется заявлением о новом restore.

## Выполненная локальная проверка

| Проверка | Результат |
| --- | --- |
| Full pytest из backend, browser flag=1 | **145 passed in 122.83s**, 124 unit/integration + 21 E2E; disposable PostgreSQL 17 на loopback |
| JS | `node --check frontend/app.js`: PASS |
| Python dependencies | Local и production `pip check`: PASS |
| Vulnerability audit | `pip-audit 2.10.1 --strict --no-deps --disable-pip` по точным версиям 76 локальных external packages, editable backend исключён: **No known vulnerabilities found** |
| PowerShell | Parser всех 36 `.ps1`: 0 errors |
| Linux shell | `bash -n` всех 7 `.sh`: PASS |
| Compose | Local, production, Oracle overlay и free-demo: `config --quiet` PASS |
| OpenAPI policy | 64-operation registry matches method/path; ADMIN=29, Viewer-level=35 |

Первый pytest был остановлен без результата при недоступной штатной локальной PostgreSQL. Успешный прогон выполнен после запуска отдельного temporary container `assetguard-audit-20261006-postgres`, port 55326. Fixture сама создала/удалила session database. Локальный Vision продолжал работать; operational DB и production не использовались для тестовых записей.

Проверки Python source syntax, итоговых Markdown links и focused documentation policy перечислены в финальной сверке ниже. Полный сбор/пересборка нового application image не требовался для Markdown-изменения. Gitleaks проверен через текущий опубликованный CI; отдельный свежий local whole-history scan здесь не заявляется. Real-model Vision smoke сохраняется как подтверждённый результат 4 октября (23 detections), а не как запуск этого аудита.

## Исправленные расхождения документации

| Расхождение | Что исправлено |
| --- | --- |
| README/test docs: 103/122 backend, 16 E2E | Свежий результат 124+21=145; cases отделены от test functions |
| README/security/UX: 60/63 admin operations | Текущие 64 operations / 57 paths; полный 73-operation reference |
| Database/source layout: head 0025 | Текущий head 0026 и notification module/worker |
| QR одновременно готов и P1 | Cabinet QR, scan/manual fallback и session draft завершены; PWA/offline остаются открыты |
| 0.1.7 и native service как текущий Agent | Candidate 0.1.8: SYSTEM task, local collector/FIFO и disabled daemon; published prerelease 0.1.6 отдельно |
| Production docs только про 93ff8ed/0025 | Current application f4f56e7/checkpoint dca5a86/0026; старые acceptance records помечены историческими |
| VIEWER описан как всегда read-only | Viewer-level route + resource grant; EDITOR может разрешить asset/physical writes, technical baseline остаётся ADMIN-only |
| E2E запуск из root и обязательный API :8000 | Запуск из backend, local PostgreSQL, fixture-managed disposable DB/live server |
| RawInventory «никогда не меняется» | Immutable evidence fields; processing metadata обновляется workflow |
| Строго изолированные module tables в architecture | Реальные организационные границы modular monolith/shared transactions |
| Устаревшие UX menus/prompt планы | Четыре рабочие раздела, шесть room tabs, task tabs и текущие managed forms/states |
| Полное WCAG/production readiness из E2E | Ограничения Chromium/lab и самостоятельные manual/fleet/capacity gates описаны явно |

## Открытые инженерные и продуктовые риски

| Приоритет | Подтверждённая граница | Следующее доказательство |
| --- | --- | --- |
| P0 rollout | Agent 0.1.8 принят на одном PC; полных 3–5-PC наборов нет | Fleet phases, physical offline/reboot/reimage, update и итоговая readiness |
| P0 rollout | EXE 0.1.8 NotSigned; финальная readiness установка ранее отменена UAC; managed rollback отсутствует | Signed release, реальное update/rollback, artifacts/manifest |
| P0 rollout | Retention/export/delete policy не утверждена; triggers блокируют обычное удаление evidence | Governance по классам данных и tested archive/export/delete procedure |
| P0 rollout | Scoped ADMIN/negative tests есть; platform/onboarding и legacy fallback открыты | Приёмка двух организаций, явные полномочия и migration/disable plan |
| P0 rollout | Staging/failover/RTO/RPO и manual UI acceptance открыты | Отдельное staging outage/recovery и 3–5 сотрудников/браузеры/accessibility |
| P1 | Не все writes имеют idempotency key; lost response может повторить act/history | Recovery/idempotency contract и tests критичных writes |
| P1 | Full admin audit, MFA/SSO, protection rules, SAST/container scan/SBOM отсутствуют | Выделенный security/release этап с измеримой приёмкой |
| P1/P2 | Assets/endpoints whole-list, single-process IP limiter/NAT, 50 snapshots per endpoint, frequent capture storage | Capacity/soak/retention tests и server pagination decision |
| P2 | Vision local demo, Oracle без ML, image volume вне SQL backup, отсутствует accuracy dataset | Inference/object storage/image recovery/quality benchmarks до production photos |

Agent candidate `0.1.8`: **2 114 556 bytes**, Authenticode **NotSigned**, SHA-256 `BCD24D903FDB7C03EACB51E38F3BE653938DD905B0683F360A0BC8B412D3F50F`, перепроверены локально. [Technical debt](../technical-debt.md), [roadmap](../product/production-readiness-roadmap.md), [fleet](../operations/agent-fleet-pilot.md).

## История связанных чатов

Получен текущий список чатов и archived list (архивных записей нет). Просмотрены доступные turns/итоги **15 связанных чатов**; для длинных чатов — несколько страниц последних этапов и нужные исторические checkpoint сообщения. История — основание для восстановления решений; текущие факты перепроверены кодом/tests/server/GitHub. Секреты и исходные сообщения в файлы проекта не переносились.

| Чат (название из приложения) | Контекст, использованный в сверке |
| --- | --- |
| Изучи этап и составь план | Новейшие Ledger/QR/simplification stages, publication f4f56e7/dca5a86, remaining gates |
| Провести полный аудит проекта | Предыдущий repo/R2/backup аудит и последовательность исправления старого токена |
| Изучи ProofPilot и внедри скилл | Историческое разделение pilot MVP и продуктовой готовности; venture score не выдаётся за текущую engineering оценку |
| Проверь сбой сайта AssetGuard | Browser GET /glpi-agent 404 и protected machine-to-machine contract |
| Изучить AssetGuard и расставить прио | UX/API приоритеты и границы Vision |
| Составить чеклист и план проекта | Физические операции и ранний task navigation; старые test counts исторические |
| Продолжить этапы пилота и релиза | Documentation sync, fleet/release/governance gates |
| Продолжить работу над AssetGuard | Published installer 0.1.6 и GLPI version lock |
| Определить этап проекта | Route/access matrix, backup/monitor checkpoint |
| Составить план доработки AssetGuard | Продолжение существующего продукта и ограничение изменений Vision |
| Провести обзор документации | Vision MVP/PR history; merged state проверяется по текущему Git |
| Исследовать основу и архитектуру MVP | Первичные требования, source boundary и completion checklist |
| Упростить дизайн админки | Обсуждение доказательной базы и демонстрационных материалов; chat DOCX не является локальным source-of-truth |
| Идея AssetGuard | Три источника наблюдений: Agent, QR и Vision; гипотеза не превращена в гарантию detection |
| Asset Guard слабые места | Исторические продуктовые ограничения и необходимость объяснимого школьного workflow |

Дополнительно проверенный чат «Итоги подготовки к батлу» содержал LifecycleKASE и исключён из AssetGuard conclusions. История VKO/LifecycleKASE не перенесена в требования этого проекта. Доступные sandbox DOCX из ChatGPT не переписывались как текущая проектная документация; исходные условия/ссылки остаются в тех чатах.

## Документационные решения

Исторические reports/исследования/requirements сохраняют исходные даты и свидетельства, получают явный указатель на текущий checklist. Принятые восемь ADR не переписаны; новую архитектуру аудит не вводит. API reference получен из текущего OpenAPI и executable policy, без новой runtime dependency. Current guides содержат дату сверки, а publication/application/installer/schema различаются.

## Финальная сверка

| Проверка после обновления документации | Результат |
| --- | --- |
| Охват Markdown | Все 90 файлов: 77 изменённых исходных, 9 сохранённых ADR/template и 4 новых |
| Локальные Markdown-ссылки | 1276 file/directory links, отсутствующих targets нет; anchors и HTTP status внешних ссылок эта проверка не проверяет |
| Python source syntax | Все 108 tracked `.py` разобраны через AST, syntax errors отсутствуют |
| Focused route/document policy | `tests/unit/test_admin_route_contract.py`: **14 passed in 1.35s** после основной актуализации |
| Сохранность исходников/артефактов | SHA-256 всех non-Markdown tracked файлов совпадают с исходным inventory; восемь ADR и template также побайтно сохранены |
| Git formatting | `git diff --check`: PASS |
| Test infrastructure | Созданный для аудита PostgreSQL container остановлен и удалён; обычный локальный Vision и production не пересоздавались |

Self-review уточнил различие named-session logout и shared-token authentication, текущий Windows venv/fallback, путь к импорту и QR в Ledger и исторические версии deployment/installer. Результаты старых испытаний не переименованы в новые, accepted ADR не переписаны. Runtime code, tests, dependencies и configuration не изменены.

Эти изменения остаются в локальной рабочей копии; GitHub CI выше относится к опубликованным `f4f56e7`/`dca5a86`. Commit/push и deployment в этом аудите не выполнялись. Открытые fleet, signing, governance, multi-tenant onboarding, manual UI и staging gates не закрываются обновлением документации.
