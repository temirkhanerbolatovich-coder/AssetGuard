# AssetGuard: приёмка Telegram и подготовка UI/UX

Дата клиента: 2026-10-05, Asia/Qyzylorda UTC+5. Серверные timestamps ниже — UTC.

## Область и версия

Пользователь выбрал новые инциденты плюс проблемы Agent/сервера и разрешил настоящую тестовую отправку в ранее настроенный чат. Application commit: `0b90607816a79fb72e4f9ef2969814d5a0998b5c`, main. Production schema: `0026_telegram_notifications`.

Runtime image: `sha256:195d94d16c8feb9702531498df1023aa42718b3086f03ce55516290ed213a517`, tag `assetguard-api:candidate-0b90607`. Сохранён предыдущий image `assetguard-api:rollback-pre0b90607-20261005` (приложение `93ff8ed`, схема `0025`). Секреты бота/чата не входят в этот протокол.

## Автоматическая проверка

- Локально: 96 unit/integration passed; 2 browser E2E passed; pip check, JS syntax, Bash syntax каждого Linux script и git diff check прошли.
- [GitHub CI на application commit](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37227553441): success, attempt 2. Test job: 96 passed, 2 browser E2E, pip check, dependency audit «No known vulnerabilities found», PowerShell/JS/Linux/Compose checks.
- Первый secret-scan запуск не дошёл до сканирования: unauthenticated GitHub API rate-limit вызвал ошибочную необходимость лицензии. Повторный запуск завершился success; проверка не отключалась и allowlist не расширялся.
- Real-model smoke в этом push был skipped согласно существующему workflow. Vision не менялась; прежний manual smoke на `93ff8ed` остаётся предыдущим свидетельством, не новой проверкой модели.

Domain tests проверяют технический ingestion и физический обход → outbox, транзакционный rollback, уникальное событие, 429/retry_after, restart, отсутствие повторной отправки, SKIP LOCKED и organization/location scope. Реальные business incidents в production ради теста не создавались.

## Backup и репетиция

Pre-deployment encrypted R2 object: `assetguard-production-20261004-190646.sql.agbackup`. Изолированный restore прошёл: schema `0025`, assets=216, endpoints=11.

На этой копии выполнено `0025 → 0026 → 0025 → 0026`. Сравнение counts и row fingerprints **всех прежних application tables** после upgrade и downgrade совпало. Старый API запустился обычным CMD на downgraded `0025`, readiness 200. Новый API запустился на `0026`; operations/assets/re-enrolments дали защищённые HTTP 200, notification counters были нулевыми. Production DB для репетиции не использовалась.

Post-deployment encrypted R2 object: `assetguard-production-20261004-192557.sql.agbackup`. Изолированный off-site restore прошёл в `2026-10-04 19:27:02 UTC`: schema `0026`, assets=216, endpoints=11, service result success. Скрипт проверяет revision и основные entities; отдельное сравнение payload очереди при этом restore не выполнялось.

## Production acceptance

Переключён только API; PostgreSQL и Caddy container IDs сохранились. Deployment завершился `2026-10-04T19:25:12+00:00`.

- Public `/health` и `/health/ready`: 200; public hashes index/app/styles совпадают с image.
- 60 admin operations; защищённые assets/credentials/re-enrolments: HTTP 200 с credentials и 401 без них.
- Counts: 216 assets, 11 endpoints, 51 raw inventories, 51 snapshots, 17 credentials, 0 re-enrolment requests. Существующие данные не исправлялись для прохождения проверки.
- Operations: 1 online, 10 stale, 0 offline/conflicts/failed ingests. Эти 10 ПК по-прежнему требуют fleet acceptance.
- Monitor source/install byte comparison PASS, таймер раз в 5 минут активен; два последовательных normal запуска подавили неизменившееся сообщение.
- Установлен `assetguard-notifications.timer` раз в минуту. Организация текущего чата указана явно; чужие/неназначенные события не отправляются.

## Реальная доставка

Один контролируемый `--enqueue-test`: `sent=1, retry_scheduled=0`. Немедленный запуск без флага: `sent=0, retry_scheduled=0`.

Запись в БД: `status=SENT`, `attempts=1`, `telegram_message_id=8`, `sent_at=2026-10-04T19:25:06.178269+00:00`. Destination chat проверен worker; сообщение принадлежит ожидаемой организации. Пользователь отдельно подтвердил: **«Да, пришло»**.

Автоматический запуск таймера `19:25:50 → 19:26:10 UTC`: `sent=0, retry_scheduled=0`, service result success. Сохранённая запись не была отправлена заново. Это подтверждение штатной дедупликации, а не exactly-once guarantee при любом crash.

## UI/UX и следующий этап

Подготовлено отдельное [ТЗ](../docs/product/ui-ux-modernization-spec.md): текущие наблюдения, первичные источники Linear/Carbon/Grafana/Snipe-IT/GOV.UK/W3C, экранные требования, роли, визуальные tokens, состояния, адаптивность, критерии доступности и приёмки. Старая документация и original requirements не заменены; код интерфейса в этом release не модернизировался.

Порядок: 1) каркас/вход/состояния; 2) реестр и единый центр инцидентов; 3) кабинеты/обход/импорт; 4) Agent/admin/доставка; 5) keyboard/mobile/performance/usability приёмка. Новые отсутствующие API потребуют собственных scoped tests.

## Ограничения и откат

At-least-once допускает дубль после Telegram acceptance до DB commit. Нет сообщений о каждом изменении статуса инцидента/восстановлении сервера, индивидуального журнала Agent transitions, UI управления очередью или автоматического retention. Сводный Agent monitor может не заметить смену конкретного проблемного ПК при неизменном числе проблем. SENT не доказывает прочтение.

Rollback image требует schema downgrade до `0025`: queue table будет удалена, включая pending events. Перед откатом сохранять свежий encrypted backup и отдельно решить судьбу очереди; переключение старого image без согласования schema недостаточно. Общие fleet, installer signing, multi-school и Vision production gates остаются открыты.

[Настройка и проверки Telegram](../docs/features/telegram-notifications.md), [ADR-007](../docs/decisions/ADR-007-telegram-outbox.md), [актуальный checklist](../docs/product/current-project-checklist.md).
