# AssetGuard: второй этап UI/UX

> **Исторический документ.** Даты, SHA, измерения и исходные требования ниже относятся к описанному этапу. Сверка указателя выполнена 2026-10-06; текущее состояние и оставшаяся работа — в [checklist](../docs/product/current-project-checklist.md) и [аудите](../docs/quality/project-audit-2026-10-06.md).

Дата клиента: 2026-10-05, Asia/Qyzylorda UTC+5. Серверные timestamps — UTC.

## Версия и область

Application commit `c254125dd3919658dd5ba13d061a645f0729c2df`, main. Реестр/карточки и общий центр технических/физических инцидентов, приоритетные задачи, protected read API. [Контракт функции](../docs/features/registry-and-incident-center.md), [ТЗ](../docs/product/ui-ux-modernization-spec.md).

Новых UI-зависимостей и миграции нет: schema `0026_telegram_notifications`. Baseline, роли, бизнес-операции имущества, модель/inference/storage Vision и Telegram worker сохраняются. Два GET расширяют матрицу до 62 операций; evidence читает исходный immutable обход.

## Проверка

- Локально: **104 passed in 68.98 s**, 97 backend + 7 browser E2E. После изменения оформления evidence дополнительно получен актуальный preview и passed один сквозной E2E.
- [Application GitHub CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37243615993): success; **97 backend passed in 15.20 s**, **7 browser E2E passed in 20.80 s**. Secret scan, pip check, dependency audit, JS, PowerShell/Linux syntax и Compose validation прошли. Audit: No known vulnerabilities found.
- Локально `node --check frontend/app.js`, `git diff --check`, относительные ссылки изменённых документов: PASS.
- Browser E2E: 44 групповые позиции, два кабинета с одинаковым номером в разных корпусах, принтер без Agent и компьютер с настоящим ingestion/baseline/change flow. Совместные поиск/сортировка/фильтры, pagination, возврат к прежнему списку, оба вида инцидентов, прямой physical URL после reload, частичное списание с количеством 3→2, единственное решение и PDF-акт.
- Tenant/location negative tests: две организации, VIEWER/ADMIN, отсутствие grants, скрытый кабинет своей школы и даже некорректный foreign-room grant. Исходные expected/affected quantities, inspector и comment проверены.
- Authenticated synthetic previews визуально проверены; узкие экраны 320/390/768/1366 px. Реестр/центр и карточка не создают горизонтальную прокрутку body. [Реестр](ui-stage2-preview-2026-10-05/registry-desktop.png), [центр на телефоне](ui-stage2-preview-2026-10-05/incidents-mobile.png), [доказательство обхода](ui-stage2-preview-2026-10-05/physical-incident-desktop.png).
- Real-model smoke на push skipped по workflow; Vision не изменён. Полная WCAG/zoom/performance/usability приёмка не заявляется.

## Перед переключением

Encrypted R2 object `assetguard-production-20261004-232209.sql.agbackup`. Isolated off-site restore PASS в `2026-10-04 23:22:48 UTC`: revision `0026_telegram_notifications`, assets=216, endpoints=11; оба service result success/inactive. Исходная рабочая версия `d8f6a63`, image `sha256:00d6d2408f48586c2c72df8b41f5dd8eed72d6621e51830741d3609b88d2f244`; сохранена для отката как `assetguard-api:rollback-prec254125-20261005`. Новый upgrade/downgrade rehearsal не нужен, схема не меняется.

## Production acceptance

Deployment acceptance завершён в **2026-10-04T23:34:08+00:00**. Runtime image `sha256:9de1e92039d0e6ed6e5d908f163da7517f08c6fb04616f89212c686f5640ceef`, tag `assetguard-api:candidate-c254125`. Candidate `pip check`: No broken requirements found. Exact commit/image и свежесть backup проверены перед переключением.

- Пересоздан только API; container IDs PostgreSQL/Caddy сохранились. Monitor/notifications timers приостановлены; текущие jobs завершились естественно, без убийства worker. После приёмки все четыре backup/restore/monitor/notifications timers active.
- Public `/health` и `/health/ready`: HTTP 200. Hash публичных файлов совпадает с image: index `0198b2ec97f5bcdefdebd80842abe26c1160fa2d6a3e0547152a62f11963bb32`, app.js `baffcab3fedc267b8a1c9271653e02dbd96ae71b3ad2320b9696631a94046454`, styles `117f71cf60d6c5163ee1d33a928ac13475bc7ce153f3880ed20a7ee0c98096ba`.
- OpenAPI содержит **62 admin operations**. Assets/credentials/re-enrolments/physical-incidents list: HTTP 200 с действующим credential и HTTP 401 без него. Missing physical incident: HTTP 404. Реальных физических инцидентов в production сейчас **0**; положительный evidence/decision/act сценарий принят в изолированных integration/E2E, искусственные инциденты на production не создавались.
- Публичный anonymous browser smoke: сохранён прямой `#physical-incident` URL до входа, workspace скрыт, отсутствуют private requests и page errors; пароль/required-field controls и ширины 320/360/390/768/1024/1366/1920 px: PASS. [Снимок публичного входа](ui-stage2-preview-2026-10-05/public-login-desktop.png) просмотрен.
- **Authenticated production browser read-only**: реестр рисует не более 20 строк, переход на страницу 2, карточка и возврат на страницу 2, пустой поиск/сброс; обзор, единый центр и физический фильтр; body без overflow на 320/390/768/1366 px, включая раскрытые фильтры 320/390. Page errors=0. Использован действующий bootstrap credential только в памяти процесса, без вывода/сохранения; production authenticated screenshots не снимались. Именованный login/logout по-прежнему проверен настоящими API в изолированных E2E; новая production named session не создавалась.
- Schema `0026_telegram_notifications`; counts: **216 assets, 11 endpoints, 51 raw inventories, 51 snapshots, 17 credentials, 0 re-enrolments, 1 Telegram queue row**. Сохранились исходные данные.
- Operations: **1 online, 10 stale, 0 offline/conflicts/failed ingests; pending=0/retrying=0**. Fleet readiness из этих counts не следует.
- Telegram: прежняя запись **SENT, attempts=1, message_id=8**, sent_at `2026-10-04T19:25:06.178269+00:00`; worker в 23:34:04, 23:35:06 и 23:36:07 UTC сообщил sent=0/retry_scheduled=0; новое тестовое сообщение не создавалось. Queue/read-only dedup evidence PASS. Monitor source/install byte comparison PASS.

Post-deployment encrypted R2 object: **assetguard-production-20261004-233448.sql.agbackup**. Isolated off-site restore PASS в **2026-10-04 23:35:26 UTC**: schema `0026`, assets=216, endpoints=11. Backup/restore result success, ExecMainStatus=0, inactive; четыре timers active. Прежний `d8f6a63` image сохранён; application rollback использует ту же schema и очередь.

Последующая синхронизация документов не пересобирает и не меняет application image `c254125`.

## Границы и следующий шаг

Этап UI/UX 2 завершает реестр, карточки и центр инцидентов. Следующий этап 3 — кабинет/обход и импорт: мобильный ввод результатов, quantity/error review, preview/apply и понятный итог. API списков пока загружает все доступные записи, pagination ограничивает DOM; производительность 1000+ позиций не измерена. Фильтры сохраняются внутри текущей сессии, но не после reload/в URL. Повторный submit блокируется UI; произвольным API-клиентам новая idempotency guarantee не предоставляется.

Fleet test 3–5 реальных ПК, installer 0.1.7, multi-school acceptance и production Vision host остаются самостоятельными задачами. PostgreSQL backup не включает изображения Vision; restore проверяет schema и основные counts, а не fingerprints всех строк.
