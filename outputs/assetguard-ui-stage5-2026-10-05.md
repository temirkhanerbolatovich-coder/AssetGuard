# AssetGuard — UI/UX этап 5: техническая приёмка

Дата: 2026-10-05. Статус: локальные проверки пройдены; публикация/CI/production ожидаются. Полная приёмка этапа 5 не заявлена: ручной zoom/screen reader, representative performance и usability с сотрудниками ещё не проведены.

## Точка продолжения

Начальная ветка main была чистой, application `45d739b`, documentation HEAD `cfbe830`. Сервер отвечал по HTTPS, четыре timers были active; этапы UI 1–4 приняты. Telegram ранее подтверждён пользователем, его тест повторно не отправляется. БД/публичный контракт: `0026_telegram_notifications`, 63 защищённые операции. На этом этапе изменяются CSS/HTML и проверки; логика Vision и исходное ТЗ сохраняются.

## Исправления и доказательства

До исправления обычные подписи имели contrast около 4.05:1, muted текст на отдельных поверхностях около 4.28:1, input border около 1.65:1. CSS reset input:focus скрывал прежнюю keyboard outline; девять диалогов не были связаны с заголовками. Обновлены цвета muted/eyebrow/border/hover, задана сплошная 3 px outline, связывание всех 11 диалогов и прокрутка длинных форм. На коротком viewport header и toast не перекрывают поля. Высота вкладок ≥44 px.

Контраст измерен по computed colors с alpha compositing на однотонных поверхностях: вход и семь основных разделов, также заполненный реестр четырёх ролей и synthetic capacity. После исправления ошибок в измеренной выборке нет. Минимум текста по пустым разделам: **5.162:1**, границ текстовых полей: **3.583:1**. [Исходные измерения после исправления](ui-stage5-measurements-2026-10-05/contrast.json).

Проверены семь ширин 320…1920 CSS px, короткие viewport 640×400/320×256, Tab/Shift+Tab/Enter/Space/Escape, mobile menu, modal focus/return, reduced motion и доступные подписи полей. ADMIN/VIEWER/LOCATION_MANAGER/INVENTORY_CLERK проходят login → search/card → return → logout, чужой asset/room возвращает 404; очередь разрешена только ADMIN. Новые тесты не отправляют Telegram.

Скриншоты проверены визуально на синтетической базе: [desktop](ui-stage5-preview-2026-10-05/keyboard-1366x900.png), [mobile](ui-stage5-preview-2026-10-05/keyboard-390x900.png), [короткий viewport](ui-stage5-preview-2026-10-05/keyboard-320x256.png). Это не production данные.

## Лабораторный замер

Windows, Intel Core i5-12450H; Chromium 153.0.8010.12 headless, viewport 1366×900, reduced motion, localhost API/PostgreSQL, CPU/network throttling не используется. Synthetic assets создаются только в isolated disposable DB.

| Assets | Cold workspace, ms | Warm refresh, ms | DOM rows | Document/login LCP, ms | CLS | Max recorded event, ms |
| --- | --- | --- | --- | --- | --- | --- |
| 216 | 862.9 | 344.6 | 20 | 68.0 | 0.0000 | 16 |
| 1000 | 1366.4 | 1367.7 | 20 | 80.0 | 0.0060 | 24 |

Cold/warm значения — время до готового реестра, не LCP. Document LCP обычно относится к входу: его нельзя переносить на authenticated workspace. Event durations ≥16 ms не являются полевым INP. В этих прогонах long tasks не записаны; реестр ограничен 20 DOM строками, pagination/search/filter return работают. Это отдельные lab runs, не p75, не throttled mobile и не нагрузочный тест нескольких школ. Assets/endpoints пока загружаются целиком. [216 записей](ui-stage5-measurements-2026-10-05/capacity-216.json), [1000 записей](ui-stage5-measurements-2026-10-05/capacity-1000.json).

## Валидация и документы

Локально: **118 passed** (102 unit/integration + 16 browser E2E); JavaScript syntax и git diff --check прошли. Обновлены testing strategy, design system, architecture overview (outbox/schema/backup boundary), UX workflow, UI spec, README/checklist и changelog. Новые [методика/ограничения и протокол usability](../docs/testing/ui-acceptance.md) описывают, что ещё необходимо проверить.

Новая архитектура, dependency и migration не нужны: сохранены native controls, existing pagination и текущий stack. Browser zoom 200%/400%, NVDA/реальные мобильные устройства, representative LCP/INP/CLS и ≥90% usability success остаются открытыми. Fleet 3–5 PCs, десять stale endpoints, подпись/публикация installer 0.1.7 и Vision production — самостоятельные задачи.

## Публикация и production

Ожидается после локальной приёмки. Runtime commit/image, GitHub CI, pre/post encrypted R2 restore, read-only live API/UI и timers будут записаны по факту; production writes для UI acceptance не нужны.
