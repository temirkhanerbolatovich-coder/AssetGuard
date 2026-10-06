# AssetGuard — UI/UX 3: кабинеты, обход и импорт

> **Исторический документ.** Даты, SHA, измерения и исходные требования ниже относятся к описанному этапу. Сверка указателя выполнена 2026-10-06; текущее состояние и оставшаяся работа — в [checklist](../docs/product/current-project-checklist.md) и [аудите](../docs/quality/project-audit-2026-10-06.md).

Дата клиента: 2026-10-05 (UTC+5). Статус: **этап UI/UX 3 принят на production**. API deployment **2026-10-05T00:29:25+00:00**; authenticated browser и послерелизный off-site restore прошли.

## Изменения

- Каждая позиция обхода начинает с «Не проверено», ввод количества проверяется до итога; запись происходит только после подтверждения. Ошибки оставляют ввод. После сохранения перечитывается кабинет, доступны результат, история и инциденты.
- Excel/PDF preview: scope, исходные строки/страницы, новые/обновляемые/требующие внимания позиции, выбор и исключения; мобильные карточки и доступные действия. Успех отделён от последующей ошибки refresh.
- Файл с неверными строками атомарно отклоняется; дубликаты обычного PDF не скрываются. Apply создаёт/находит canonical кабинет. Старый формат без колонок локации сохраняет её; акты MOVE/WRITE_OFF приоритетны.
- Принтер/проектор сохраняют canonical тип при повторной нормализации. Очищаются данные новых форм при выходе, прежний контекст кабинета не используется при ошибке другого кабинета.
- Original ТЗ, Vision, schema 0026 и набор 62 admin operations не изменены. Новые зависимости не добавлены.

## Локальные доказательства

`ASSETGUARD_RUN_BROWSER_E2E=1 python -m pytest tests/unit tests/integration tests/e2e`: **109 passed, 62.23 s** (101 backend + 8 browser E2E). Изменение исключительно искусственного пароля fixture дополнительно проверено: import scope **5 passed, 2.79 s**. `node --check frontend/app.js`, `git diff --check` и 75 локальных ссылок документации прошли.

Изолированный E2E проверил: две ошибки строк без записи; preview 4/selected 3; первый apply 503 сохраняет исключение, повторный apply создаёт 3; повторный файл обновляет 3 и не дублирует активы; один canonical кабинет; обход не отправляется до итога; неверные количество/непроверенные строки отклоняются; 503 сохраняет review, возврат сохраняет ввод; двойной submit создаёт один акт и два физических инцидента; после записи и reload виден итог. Ширины 320/390/768/1366, без page errors. Реальные записи выполнялись только в тестовой БД, Telegram worker там не запускался.

Синтетические снимки: [preview desktop](ui-stage3-preview-2026-10-05/import-preview-desktop.png), [mobile](ui-stage3-preview-2026-10-05/import-preview-mobile.png), [строки mobile](ui-stage3-preview-2026-10-05/import-rows-mobile.png), [review desktop](ui-stage3-preview-2026-10-05/inspection-review-desktop.png), [mobile](ui-stage3-preview-2026-10-05/inspection-review-mobile.png), [результат desktop](ui-stage3-preview-2026-10-05/inspection-result-desktop.png), [mobile](ui-stage3-preview-2026-10-05/inspection-result-mobile.png). Просмотрены для layout review, исторические снимки этапов 1/2 сохранены.

## CI

Первая попытка 37246515359 на d1f6350 завершилась failure из-за Secret scan. Secret scan обнаружил artificial fixture password как generic-api-key. Fixture исправлена в 2ae4b01, без исключений/allowlist или отключения сканирования; application code между этими commit не менялся. Application release **2ae4b01da2013b49f4d7fe4ab78718b3099b7b59**, CI **37246722604 success**: Secret scan success; test job success, pip check «No broken requirements», audit «No known vulnerabilities», **101 backend passed (24.11 s) + 8 browser passed (27.39 s)**. Real-model smoke на push штатно skipped; Vision не изменялся. Полная локальная проверка 109 passed выполнена до правки fixture; 5 import scope tests повторены после неё.

## Backup и rollback

Pre-release backup: **assetguard-production-20261005-000815.sql.agbackup**. Off-site isolated restore PASS **2026-10-05 00:09:15 UTC**, schema **0026_telegram_notifications**, **216 assets / 11 endpoints**, Result success / ExecMainStatus 0. Прежний runtime: c254125, image sha256:9de1e92039d0e6ed6e5d908f163da7517f08c6fb04616f89212c686f5640ceef. Runtime и rollback сохранены; послерелизная копия и восстановление проверены ниже.

## Ограничения и следующий этап

API обхода не имеет ключа идемпотентности: при потере ответа сначала проверяется история. Повторный импорт не дублирует карточки, но может добавить событие обновления. Черновик не сохраняется после отмены/logout/reload; OCR требует ручной сверки. Сохранены существующие границы ожидания HTTP writes/OCR и последних 50 обходов. Полная accessibility/zoom/performance/usability приёмка остаётся этапом 5; fleet 3–5 ПК, installer 0.1.7 и Vision production — отдельные задачи. Следующий UI/UX этап 4: проблемные ПК Agent, re-enrolment/credentials, users/grants и прозрачные агрегаты доставки.

## Frontend checksums принятого релиза

- index.html: `517d00c4d7f2808a31deedfb3e59dcbed8532492b3470ebd7668380d25dcadb4`
- app.js: `973073f864e07aa2fd19a1bb7e0edf5bafa101607d87f80e782f9db46690ebf8`
- styles.css: `fefd1fc071421d9d8f149ce78f07afa0b0c3c3cd8a594a5835218c8cb4e34944`

SHA-256 canonical Git blobs на 2ae4b01 совпали с публичным endpoint и установленным frontend контейнера. Локальный Windows checkout использует CRLF и не служит источником canonical hashes.

## Production API acceptance

Runtime **2ae4b01**, candidate `assetguard-api:candidate-2ae4b01`, image **sha256:47753c16d27298cac2462018362d61463e64b815e27cc66e8f45031b5a66f7f4**. Rollback tag `assetguard-api:rollback-pre2ae4b01-20261005` сохраняет прежний c254125 image. API обновлён без пересоздания PostgreSQL/Caddy; monitor source/install byte comparison PASS. Candidate pip check PASS.

Public health/ready 200, canonical frontend hashes совпали, OpenAPI **62 admin operations**. Защищённые assets/agent credentials/re-enrolments/physical incidents возвращают 200 авторизованно и 401 без входа; missing physical UUID 404. Existing room workspace/inspection history GET 200; физических production инцидентов нет, positive write flow проверен локально. Schema **0026_telegram_notifications**.

Counts: **216 assets, 11 endpoints, 51 raw inventories, 51 snapshots, 17 credentials, 0 re-enrolments, 1 queue row**. Operations: **1 online / 10 stale / 0 offline / 0 identity conflicts**, failed ingest 0, pending/retrying 0. Stale отражает отсутствие свежих отчётов; этот UI release не закрывает fleet readiness.

Telegram: прежний test **SENT, attempts=1, message_id=8**, sent_at **2026-10-04T19:25:06.178269+00:00**. Normal worker запущен без enqueue, persistent non-repeat PASS. Новых реальных сообщений или искусственных production инцидентов для этой приёмки не создавалось.

Public browser: anonymous sign-in, protected deep link сохранён, password toggle/required input, ширины **320/360/390/768/1024/1366/1920**, нулевые page errors и отсутствие protected reads до входа — PASS. Снимок public-login-desktop содержит только анонимный экран.

## Authenticated production browser и restore

Вошедший bootstrap ADMIN прочитал существующий кабинет/имущество. Начальные результаты пусты, незаполненные строки блокируют переход; локальный review и back сохраняют значения; cancel закрывает форму до POST. Import screen и controls доступны. Check/review/import widths **320/390/768/1366 px**, zero page errors и **zero admin mutations** — PASS. Private screenshots и загрузка ведомости/apply на production не выполнялись. Positive import/inspection writes подтверждены изолированным E2E и CI.

Post-release backup **assetguard-production-20261005-003054.sql.agbackup**. Off-site isolated restore **PASS 2026-10-05 00:31:38 UTC**, schema **0026_telegram_notifications**, **216 assets / 11 endpoints**. Backup/restore jobs: **Result=success, ExecMainStatus=0**, inactive после выполнения.

Все четыре timers **backup / restore-rehearsal / monitor / notifications active**. Normal notification runs **00:29:07, 00:30:14, 00:31:21 UTC**: **sent=0, retry_scheduled=0**; persistent queue сохранила одну подтверждённую попытку прежнего теста. Docker runtime image после restore совпал с candidate hash.

[Рабочая точка и следующий этап](../docs/product/current-project-checklist.md), [ТЗ UI/UX](../docs/product/ui-ux-modernization-spec.md), [контракт](../docs/features/rooms-inspection-and-import.md). После приёмки публикуется follow-up только документации/анонимного login preview; runtime остаётся 2ae4b01 и не пересобирается из-за документации.
