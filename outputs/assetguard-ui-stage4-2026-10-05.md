# AssetGuard — UI/UX 4: Agent и администрирование

Дата клиента: 2026-10-05 (UTC+5). Статус: **кандидат, production приёмка ожидается**. Текущий рабочий runtime остаётся `2ae4b01` до отдельного rollout.

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

Commit, CI, runtime image, public hashes, API/browser acceptance и post-release off-site backup/restore будут заполнены по фактическим результатам. Новое тестовое сообщение Telegram не отправляется; проверяется существующее SENT и штатное подавление повтора.
