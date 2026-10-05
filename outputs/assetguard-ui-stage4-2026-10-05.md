# AssetGuard — UI/UX 4: Agent и администрирование

Дата клиента: 2026-10-05 (UTC+5). Статус: **этап UI/UX 4 принят на production**. API deployment **2026-10-05T01:16:39+00:00**; API, browser и послерелизный off-site restore прошли.

## Изменения и границы

Конкретные компьютеры Agent, поиск/состояния/20 записей на странице, последнее соединение и серверный порог STALE. Привязка ключа не обозначает ONLINE. Быстрые переходы из обзора и внутри раздела; контекстные подтверждения, срок восстановления, одноразовый ключ, inline ошибки и защита повторного submit. Учётные записи, роли и активность видны рядом с назначениями.

ADMIN-only tenant-scoped очередь Telegram с фильтрами/страницами: безопасные метаданные, попытки и следующее время; без payload, получателя, bot token и message id. SENT объяснён как принятие Telegram, monitor сервера/агрегатов Agent отдельно. Чтение ничего не отправляет. [Контракт и ограничения](../docs/features/agent-administration-and-delivery.md).

Schema `0026_telegram_notifications`, 63 protected operations / 56 путей. Без новых зависимостей и изменений исходного ТЗ/Vision. Backend редактор роли/пароля/активности существует, новый UI редактор аккаунта в этот этап не входит. Полная WCAG/zoom/performance/usability проверка — следующий этап; fleet 3–5 PC и подпись/публикация installer 0.1.7 остаются отдельно.

## Локальная проверка

Полный набор: **111 passed, 67.72 s** (102 backend + 9 browser). После финальных переходов/диалогов и обработки ошибки обновления списка **9 browser passed, 37.34 s**. После проверки отключённого сотрудника новый E2E повторён: **1 passed, 9.03 s**. `node --check frontend/app.js`, `git diff --check` и 68 локальных ссылок документации прошли.

Новый E2E: 23 ПК (22 STALE), страницы/поиск; 26 сообщений с pending/retry/sent; отказ чтения 503 и успешный повтор; одно создание при double-submit; copy/Escape очищает секрет; known PC native ingestion → approve восстановления → старый ключ отозван; 409 создания пользователя сохраняет логин/пароль. Ширины 320/390/768/1024/1366, без page errors. Записи только в изолированной БД, worker Telegram там не запускался. API проверяет own/foreign/unassigned tenant, платформенную область, отказ другой роли/анонимного запроса, 422, порядок страниц, безопасные ссылки/ошибки и отсутствие payload.

Просмотрены синтетические снимки [Agent desktop](ui-stage4-preview-2026-10-05/agent-desktop.png), [mobile](ui-stage4-preview-2026-10-05/agent-mobile.png), [доставка desktop](ui-stage4-preview-2026-10-05/delivery-desktop.png), [mobile](ui-stage4-preview-2026-10-05/delivery-mobile.png), [сотрудники desktop](ui-stage4-preview-2026-10-05/access-desktop.png), [mobile](ui-stage4-preview-2026-10-05/access-mobile.png). Прежние приёмки/снимки сохранены.

## CI, публикация и production

Pre-release backup **assetguard-production-20261005-010247.sql.agbackup**, off-site isolated restore **2026-10-05 01:03:52 UTC**: schema `0026`, 216 assets / 11 endpoints, Result success / ExecMainStatus 0. Прежний runtime `2ae4b01`, image `sha256:47753c16d27298cac2462018362d61463e64b815e27cc66e8f45031b5a66f7f4`.

Application release **45d739b76121054878d5a5e20200733e6cf234e6**, [GitHub CI 37250012276](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37250012276) **success**. Secret scan success, pip check без нарушенных требований, audit без известных уязвимостей; **102 backend passed (24.09 s) + 9 browser passed (35.85 s)**. Real-model smoke на push штатно skipped; Vision не менялся.

Runtime image **sha256:acdc6d14c31fb5bcdce4c9444ca0043e2894320518db6c41a8841cd433d69d57**, tag `assetguard-api:candidate-45d739b`. Rollback `assetguard-api:rollback-pre45d739b-20261005` сохраняет прежний image 47753c16…; PostgreSQL/Caddy container IDs при rollout не менялись. Candidate pip check прошёл. Monitor source/install совпали; все четыре таймера активны.

Public health/readiness 200; image/public/Git frontend bytes совпали. OpenAPI: **63 protected operations / 56 путей**. Authenticated reads notifications/credentials/re-enrolments/assets/physical incidents 200, anonymous 401; отсутствующий физический инцидент 404. Существующий canonical кабинет/история читаются. Counts: **216 assets / 11 endpoints / 51 raw / 51 snapshots / 17 credentials / 0 re-enrolments / 1 queue row**. Agent: **1 online / 10 stale / 0 offline/conflicts/failed ingest**; порог 24 ч. Нет production физических инцидентов, их запись/решения проверены в изолированных тестах.

Anonymous browser: сохранён deep link, вход/validation/password controls, 7 ширин 320–1920, без admin/auth reads и page errors. [Public login screenshot](ui-stage4-preview-2026-10-05/public-login-desktop.png). Authenticated browser: 11 ПК/10 stale/1 online, фильтры/поиск, SENT/retry empty, переход к Telegram, контекстный отзыв/cancel, forms сотрудников/назначений; ширины 320/390/768/1024/1366. **Zero admin mutations**, без private screenshots.

Telegram: прежний подтверждённый тест остаётся **SENT, attempts=1, message_id=8, sent_at=2026-10-04T19:25:06.178269+00:00**, очередь 1. API не возвращает payload/получателя/message id/token. Нормальный worker после rollout не отправил повтор; pending/retrying 0. Новое тестовое сообщение не создавалось. Приёмка реального получения пользователем остаётся в [Telegram record](assetguard-telegram-2026-10-05.md).

Post-release backup **assetguard-production-20261005-011729.sql.agbackup**, off-site isolated restore **2026-10-05 01:18:22 UTC**: schema `0026_telegram_notifications`, **216 assets / 11 endpoints**, Result success / ExecMainStatus 0. Backup охватывает PostgreSQL; Vision volume остаётся отдельным ограничением.

## Frontend checksums принятого релиза

- index.html: `525c285c7f28b2ef7c5ec70f99afa714c3f8e17d941c156424f496d17a7cfba6`
- app.js: `1e20f7eb7ce7cc90e6209c41dce1970718002dd3f192594f846b81cd16e371cb`
- styles.css: `ee380ffacbf0ee78e9a7b0ef38b53197d9f88ad5793805efb6f381cada6d5607`

Следующий UI/UX этап **5**: клавиатура, focus/contrast/zoom, производительность и сценарии ролей; usability с 3–5 представителями ролей. Эти проверки не выдаются за выполненную WCAG сертификацию. **10 stale PC** требуют самостоятельной fleet-проверки; UI не исправляет состояние реального компьютера.
