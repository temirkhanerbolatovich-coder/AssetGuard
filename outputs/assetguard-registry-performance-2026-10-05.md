# AssetGuard — пакетное чтение сводок ПК

Дата: 2026-10-05. Продолжение технической приёмки UI/UX, этап 5.

## Исходная точка

Чистая main `065c443`, production application `18d6238`, HTTPS readiness 200. Этапы UI/UX 1–4 и автоматическая часть этапа 5 приняты; ручной zoom/screen reader/mobile и usability ещё открыты. После предыдущего исправления реестр assets сохранял запросы аппаратной истории на каждый ПК.

На production 216 assets / 11 endpoints. Два read-only вызова до изменения: assets **65 SELECT, 312.3/224.7 ms**, endpoints **105 SELECT, 293.6/337.8 ms**. Время относится только к серверной функции в read-only транзакции, без HTTP, authentication и браузера. Это малая диагностическая выборка, не p75 и не capacity acceptance.

## Изменение и ограничения

Assets/endpoints выбирают доступные объекты с Asset/Endpoint/Organization JOIN и затем читают сводки общими запросами: bounded snapshot/observations и grouped открытые changes/incidents. SQL row_number ограничивает историю последними 50 snapshots **для каждого** ПК. Пустой последний отчёт остаётся current_snapshot; комплектующие берутся отдельно по типам из последних наблюдений в окне. Сохраняются несколько RAM/storage observations одного типа, MiB/bytes и прежний статусный контракт. Отбор tenant/room выполняется до hardware чтения; room grants вычисляются однократно для списка endpoints.

API shape, permissions, схема `0026` и 63 защищённые операции сохраняются. Новые зависимости, кеш и очередь не нужны; ADR для смены архитектуры не требуется. Vision, исходное ТЗ и frontend не изменяются. Списки по-прежнему возвращаются целиком; детальные карточки читают свою историю отдельно. Не заявляется принятие performance budgets LCP/INP/CLS.

## Проверки

Шесть новых regression cases дополняют прежний query-budget: HTTP assets/endpoints с 1/30 ПК, partial/empty inventory, замена RAM, CPU/disks из предыдущего наблюдения, OPEN/UNDER_REVIEW counts и ≤5 SELECT; окно 50/51 на разных ПК; отсутствие inventory/связи с asset; scoped пользователь видит только назначенный кабинет своей организации. [Методика](../docs/testing/ui-acceptance.md).

Локально **125 passed**: 109 unit/integration и 16 browser E2E. `node --check frontend/app.js` и `git diff --check` прошли. Обновлены методика UI-приёмки, testing strategy и changelog. Application `0f67995` опубликован и принят на production; [CI 37256897869](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37256897869) success: 109 backend + 16 browser E2E, Secret scan, pip check и vulnerability audit. Real-model job штатно skipped: Vision не менялся.


## Production после изменения

| Список | SELECT до → после | Серверная функция до, ms | После, ms |
| --- | --- | --- | --- |
| 216 assets, 7 связанных ПК | 65 → **4** | 312.3 / 224.7 | 270.0 / 178.0 |
| 11 endpoints | 105 → **4** | 293.6 / 337.8 | 110.3 / 483.7 |

Digest полного ответа каждого списка совпадает во всех парных замерах до/после. Стабильно подтверждено сокращение числа запросов; длительности на 1 GB VM колеблются, устойчивое ускорение каждого вызова не заявлено. [SQL до](registry-performance-2026-10-05/sql-before.json), [после](registry-performance-2026-10-05/sql-after.json). Транзакции READ ONLY, без печати записей имущества.

Chromium 153, Windows client → public HTTPS, viewport 1366×900, no throttling, два fresh browser contexts: cold workspace **2443.8 / 2414.7 → 1915.1 / 1928.1 ms**; warm **1886.7 / 1864.3 → 1883.7 / 2394.0 ms**. В этой выборке первый вход быстрее, warm refresh не показывает устойчивого улучшения. Это время до готового реестра, не LCP/p75/полевой INP. Число HTTP reads остаётся 14; frontend порядок загрузки не менялся. [Browser до](registry-performance-2026-10-05/browser-before.json), [после](registry-performance-2026-10-05/browser-after.json).

Read-only live browser acceptance прошла: семь разделов без contrast failure, девять viewport, keyboard, pagination/card/back и cancel подтверждения с возвратом фокуса. Admin mutations=0, приватные screenshots не создавались. [Результат](registry-performance-2026-10-05/browser-acceptance.json).

Runtime `sha256:49af94c252d4d53fd815e46736f6e53750c0533747f504421f42683157a7e473`. Public readiness/health, frontend Git blob hashes, authenticated 200 и anonymous 401, missing physical incident 404 проверены; `0026`, 63 operations, 216 assets/11 endpoints. PostgreSQL/Caddy не пересозданы. Старый Telegram тест SENT, attempts=1/message_id=8 остался единственным; штатный worker не повторил его. 1 ONLINE/10 STALE по порогу 24 h; ingest failed=0, notification pending/retrying=0. Рабочих физических инцидентов нет, их сценарий проверен в isolated E2E.

До выкладки encrypted R2 `assetguard-production-20261005-025913.sql.agbackup`, isolated restore PASS **03:00:07 UTC**; после `assetguard-production-20261005-030315.sql.agbackup`, restore PASS **03:04:09 UTC**. Обе копии содержат `0026`, 216/11. Четыре timers active; rollback image `assetguard-api:rollback-pre0f67995-20261005` сохранён. [Метаданные приёмки](registry-performance-2026-10-05/release-evidence.json).

## Следующая рабочая точка

Техническая оптимизация списков принята. Ручной browser zoom 200%/400%, NVDA/реальный mobile, representative performance и usability с 3–5 сотрудниками остаются открытыми. Fleet на 3–5 ПК, разбор 10 STALE и подписанный installer 0.1.7 — отдельные gates. Пакетные SQL reads не заменяют server pagination/capacity test на большом парке и не подтверждают массовое внедрение.
