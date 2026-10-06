# AssetGuard — публикация исправлений Agent и документационного аудита

Дата приёмки: **2026-10-06 19:07:22 UTC**, **2026-10-07 00:07:22 UTC+5**. Application commit `7c45435971329cabd6382466eadca8a1540ade7d`, branch `main`. [GitHub CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37512336108): **success**.

## Объём и проверка

Опубликованы согласованная свежесть Agent, состояния без Agent/до первого отчёта, распознавание XML-версии 1.20 и полный документационный аудит. [Реализация и синтетические снимки](assetguard-agent-status-fixes-2026-10-06/report.md). Локальный набор: **170 passed** (148 backend + 22 Chromium E2E), JS/diff/Markdown links passed. Gitleaks staged scan: no leaks. GitHub application CI: API/browser tests, dependency audit, secret scan, PowerShell/Linux/Compose/JS checks passed; real-model Vision smoke корректно пропущен для push.

## Backup и выкладка

- Свежая encrypted R2 copy `assetguard-production-20261006-183238.sql.agbackup`; backup/restore services success/0. Isolated restore PASS: `0026_telegram_notifications`, assets=220, endpoints=11.
- Previous API retained as `assetguard-api:rollback-pre7c45435-20261006`. Candidate `assetguard-api:candidate-7c45435`, image `sha256:1a98957a3ef6829a3281d32c5e9130157a4e73feff730e2e4a165da7902beda1`, `pip check` passed.
- Пересоздан только API. PostgreSQL/Caddy IDs проверены до/после и совпали; volumes сохранены. Schema не менялась. При отказе приёмки rollout script возвращает previous API image; откат не понадобился.
- Monitor/notifications timers возобновлены; failed systemd units отсутствуют. Новые ключи, эталоны, тестовые инвентаризации и Telegram test messages не создавались.

## Production приёмка

Public `/`, `/health`, `/health/ready`: 200; без авторизации `/admin/endpoints`: 401, GET `/glpi-agent`: 404, XML POST: 401. Read-only API-проверка: 220 assets, 11 endpoints; freshness `{"ONLINE": 6, "STALE": 5}`. Проверены summaries, endpoint/asset details, operations и 2 workspace кабинета; 11 latest version cards корректно распознают проверенные 1.19/1.20 без изменения source_version.

Публичные байты совпадают с Linux Git checkout и принятой image:

| Файл | SHA-256 |
| --- | --- |
| `index.html` | `33e1ba8eb5069d1e0bf3b187d733a71a58818e37845f21ba69790af2f32a6ac1` |
| `app.js` | `321ab919fd508b3f903d5203c0760ea5308dd6037c58c761479d17d6f2a28753` |
| `styles.css` | `6c8aa69447cf0ea8a151542e4b4e390af7cec392b1d26f6c85ac7395bedba3d7` |

Production browser-приёмка прошла в существующей пользовательской сессии 2026-10-07 около 00:08–00:10 UTC+5. Обзор показывает 5 компьютеров без свежих данных вместо прежних 29; 24 компьютера без Agent выделены отдельной ссылкой, которая открывает соответствующий фильтр и 24 результата. Кабинет 103Б показывает 3 из 8 Agent на связи, общий статус «Требует внимания», а вкладка «Проверки» — пять устаревших отчётов и три активных Agent. В технических данных карточки сохранено `GLPI-Agent_v1.20`; ложное предупреждение об unsupported version отсутствует.

Существующая вкладка сначала сохраняла прежний интерфейс; полная навигация к опубликованному сайту загрузила новую версию, сессия восстановилась. После проверки открыта обычная страница обзора. Production screenshots остаются локально и не публикуются в GitHub. Синтетические screenshots находятся в regression report.

## Точка продолжения

Application/runtime — `7c45435`; acceptance documentation зафиксирована отдельным docs commit и не требует rebuild image. [Актуальный checklist](../docs/product/current-project-checklist.md). Релиз исправляет три UI/API-дефекта; fleet/signing/governance/onboarding/manual accessibility gates сохраняются.
