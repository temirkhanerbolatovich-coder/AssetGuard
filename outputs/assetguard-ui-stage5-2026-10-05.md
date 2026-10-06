# AssetGuard — UI/UX этап 5: техническая приёмка

> **Исторический документ.** Даты, SHA, измерения и исходные требования ниже относятся к описанному этапу. Сверка указателя выполнена 2026-10-06; текущее состояние и оставшаяся работа — в [checklist](../docs/product/current-project-checklist.md) и [аудите](../docs/quality/project-audit-2026-10-06.md).

Дата: 2026-10-05. Статус: автоматическая browser/API приёмка пройдена на production, application `18d6238`. Полная приёмка этапа 5 не заявлена: ручной zoom/screen reader, representative performance и usability с сотрудниками ещё не проведены.

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

Локально: **119 passed** (103 unit/integration + 16 browser E2E); JavaScript syntax и git diff --check прошли. Обновлены testing strategy, design system, architecture overview (outbox/schema/backup boundary), UX workflow, UI spec, README/checklist и changelog. Новые [методика/ограничения и протокол usability](../docs/testing/ui-acceptance.md) описывают, что ещё необходимо проверить.

Новая архитектура, dependency и migration не нужны: сохранены native controls, existing pagination и текущий stack. Browser zoom 200%/400%, NVDA/реальные мобильные устройства, representative LCP/INP/CLS и ≥90% usability success остаются открытыми. Fleet 3–5 PCs, десять stale endpoints, подпись/публикация installer 0.1.7 и Vision production — самостоятельные задачи.

## Публикация и production

Frontend application `166e65f` опубликован и принят на production: [CI 37253034042](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37253034042) success, 102 backend + 16 browser E2E, Secret scan/dependency audit. Runtime image `sha256:9545516cd1309009def74729729124782d126e8ab23f11aa1703cd1590a2f223`, public hashes совпали с Git blobs. Schema `0026`, 63 operations; authenticated reads 200, anonymous 401, missing physical incident 404. Рабочих физических инцидентов нет; сценарий проверен в isolated E2E.

Pre backup `assetguard-production-20261005-015018.sql.agbackup`, restore PASS 01:51:01 UTC. Post frontend backup `assetguard-production-20261005-020644.sql.agbackup`, restore PASS 02:07:53 UTC: `0026`, assets=216, endpoints=11. PostgreSQL/Caddy не пересозданы; четыре timers active. Штатный worker сохранил единственный прежний Telegram тест SENT/attempts=1/message_id=8 — новый тест не отправлен.

Public anonymous и authenticated production browser checks прошли: семь разделов без contrast failure, девять viewport, registry/card/back, Tab/Shift+Tab/Space/Escape, именованный диалог и отмена с возвратом фокуса. Zero admin mutations, приватных screenshots нет. [Public login](ui-stage5-preview-2026-10-05/public-login-desktop.png).

## Найденная задержка и устранение N+1

Первый production workspace load после выкладки занял 11112 ms. Повторные cold/warm samples: 3476/2919 и 3467/5001 ms. Самый долгий `/admin/assets`: 1578…3369 ms; это наблюдения browser resource timings, не чистое время SQL. [Исходная выборка](ui-stage5-measurements-2026-10-05/production-before-performance.json), [первая browser приёмка](ui-stage5-measurements-2026-10-05/production-before-summary.json).

Код делал отдельный endpoint lookup для каждого asset. Asset, endpoint и имя организации теперь выбираются одним LEFT JOIN, сохраняются сортировка и tenant/location filters. Уникальность связи обеспечена существующим index `uq_managed_endpoints_one_per_asset` из migration `0007`; формат ответа не меняется. Regression test проверяет 216 assets, две связи и ≤10 SELECT. Hardware summaries по привязанным ПК пока читаются отдельно; server pagination assets/endpoints остаётся открытой.

После изменения: локально **119 passed** (103 backend + 16 browser E2E); [CI 37254642307](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37254642307) success, 103 backend/16 browser, dependency check/audit и Secret scan. Application `18d6238e9e9ea496cef8bcc6199b38f76b81100f` развёрнут; runtime `sha256:080f1b2606645b40917589fa2279852651c2e6109c9148c6baa58bc10499ec9f`. Public frontend hashes остались равны Git blobs, protected contract/schema не изменились. Предыдущий runtime `166e65f` сохранён как `assetguard-api:rollback-pre18d6238-20261005`.

| Synthetic assets | Cold workspace после, ms | Warm после, ms | DOM rows |
| --- | --- | --- | --- |
| 216 | 245.9 | 231.4 | 20 |
| 1000 | 266.7 | 242.6 | 20 |

[216 assets](ui-stage5-optimized-2026-10-05/capacity-216.json), [1000 assets](ui-stage5-optimized-2026-10-05/capacity-1000.json). Это те же local hardware/network параметры; одиночные lab samples не являются performance гарантией.


## Итоговая production приёмка оптимизации

Прямой вызов deployed `list_assets` в транзакции READ ONLY: 216 assets, 7 привязанных ПК, 65 SELECT, 786.4 ms. [Query budget](ui-stage5-measurements-2026-10-05/server-query-budget.json). Измерение исключает HTTP/auth/network. Устранены lookup на каждую позицию; остальные SELECT связаны преимущественно с аппаратными summary привязанных ПК. Их пакетное чтение — следующий performance шаг, общий целевой бюджет пока не принят.

Повторные browser samples после изменения (два свежих context, по cold/warm): cold workspace **3451.3…3947.9 ms**, warm **1876.5…2908.5 ms**; `/admin/assets` **1129.0…2811.0 ms**. До изменения запрос assets занимал 1578…3369 ms. [Полные resource timings после](ui-stage5-measurements-2026-10-05/production-performance.json). Server/network load меняется, выборка мала; это не p75 и не принятие LCP/INP бюджета. [Read-only browser summary](ui-stage5-measurements-2026-10-05/production-summary.json): контраст семи заполненных разделов, девять viewport, keyboard/card/back, modal Escape/return и zero admin mutations прошли вновь.

После оптимизации fresh encrypted R2 backup `assetguard-production-20261005-022901.sql.agbackup` восстановлен в isolated DB: `0026`, assets=216, endpoints=11, PASS **2026-10-05 02:30:20 UTC**. API/public health готовы, PostgreSQL/Caddy не пересозданы, четыре timers active. Существующий Telegram тест по-прежнему SENT/attempts=1/message_id=8, новых тестовых отправок нет.

Во время получения коммита обнаружены пять старых root-owned prefix directories в `.git/objects`, мешавших Ubuntu fetch. Ownership восстановлен только в Git objects; fetch/fast-forward выполнены пользователем ubuntu. Secret configuration и рабочие данные не менялись.

Следующий шаг — ручная UI приёмка по подготовленному протоколу, затем fleet checks и installer release. Полный WCAG audit, реальный zoom/NVDA, representative performance и usability пока открыты. Документальные commits после application `18d6238` не требуют пересборки API при неизменных frontend/backend исходниках.
