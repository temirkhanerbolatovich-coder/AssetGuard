# AssetGuard: первый этап UI/UX

Дата клиента: 2026-10-05, Asia/Qyzylorda UTC+5. Серверные timestamps — UTC.

## Версия и область

Application commit: `d8f6a63baf3e03652e36ed4d2c58f77b7a626e25`, main. Основная реализация — `c62452a`; финальное исправление мобильного overflow и CI — `d8f6a63`. Backend implementation, схема `0026_telegram_notifications`, Vision model/inference/storage, роли и Telegram worker не менялись.

Отдельный вход пользователя/пароля и явный bootstrap-вариант; профиль сотрудника и область работы; loading/error/retry; bounded чтение/login/logout; очистка сессии и серверный revoke; совместимость hash-ссылок; защита от позднего ответа после смены сессии/карточки; Enter/Escape, focus и адаптивное меню. [Описание функции](../docs/features/frontend-shell-and-auth.md), [ТЗ и этапы](../docs/product/ui-ux-modernization-spec.md).

Сохраняется существующий frontend без новых зависимостей. Новые права/API и миграция не нужны. Для scoped ролей без admin-only organization API показывается «Назначенная организация», а не выполняется запрос с расширенными правами.

## Проверка

- Локальная полная проверка основной реализации: **102 passed** (96 unit/integration, 6 browser E2E). После финального CSS/CI исправления повторены **6 browser E2E: passed**.
- [GitHub CI финального application commit](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37231275721): test и Secret scan success; **96 backend passed in 22.07 s**, **6 browser E2E passed in 22.51 s**. Dependency audit: «No known vulnerabilities found»; pip check, JS, PowerShell/Linux и Compose checks прошли.
- Локально: `node --check frontend/app.js`, `git diff --check`, actionlint и синтаксис release helper прошли.
- Основной сценарий проверяет ширины **320/360/390/768/1024/1366/1920 px** до и после входа; отдельно неправильный пароль, Enter, error focus, мобильный Escape/menu, исходную ссылку, 403/503/retry, 401, session timeout, отзыв именованной сессии, выход во время чтения и ответ старой карточки.
- Первые два Linux CI запуска выявили overflow на 320 px: `white-space: nowrap` у onboarding-ссылки делал body шириной 330 px. Перенос текста разрешён, в assertion добавлены viewport и геометрия выходящих элементов; следующий CI прошёл. Проверка не ослаблялась скрытием всей горизонтальной прокрутки.
- Для secret-scan передан штатный `GITHUB_TOKEN` с прежним `contents: read`; PR comments отключены. Это устраняет повторяющийся anonymous GitHub API rate limit без bypass/allowlist. Основание: [официальный пример Gitleaks Action](https://github.com/gitleaks/gitleaks-action#usage-example).
- Real-model smoke на этом push skipped по условиям workflow. Полная WCAG/usability/performance приёмка ещё не выполнена.

## Резервная копия до переключения

Encrypted R2 object: `assetguard-production-20261004-195652.sql.agbackup`. Isolated off-site restore PASS в `2026-10-04 19:59:58 UTC`: revision `0026_telegram_notifications`, 216 assets, 11 endpoints. Backup/restore service result success. Нового upgrade/downgrade rehearsal нет: этот релиз не меняет схему.

## Production acceptance

Deployment принят в `2026-10-04T20:24:24+00:00`. Runtime image `sha256:00d6d2408f48586c2c72df8b41f5dd8eed72d6621e51830741d3609b88d2f244`, tag `assetguard-api:candidate-d8f6a63`. Предыдущий working image `0b90607` сохранён как `assetguard-api:rollback-pred8f6a63-20261005`; откат приложения сохраняет schema `0026` и очередь.

- Переключён только API; PostgreSQL и Caddy container IDs сохранились. Timers monitor/notifications приостановлены, текущим oneshot jobs позволено завершиться; после acceptance timers восстановлены.
- Public `/health` и `/health/ready`: HTTP 200. SHA-256 публичных index/app/styles совпадает с image; anonymous browser smoke показывает отдельный вход, скрытый workspace, сохранение `#devices`, переключатель пароля, требуемое поле, отсутствие private API requests и отсутствие overflow на семи ширинах. Page errors: 0. [Снимок публичного входа](ui-stage1-preview-2026-10-05/public-login-desktop.png) визуально проверен.
- 60 admin operations; assets/credentials/re-enrolments: 200 с действующим credential, 401 без него. Production named login/logout через браузер отдельно не выполнялся; этот сценарий проверен E2E с настоящими API в изолированной БД.
- Schema `0026_telegram_notifications`. Counts: 216 assets, 11 endpoints, 51 raw inventories, 51 snapshots, 17 credentials, 0 re-enrolment requests, 1 Telegram queue row.
- Operations: 1 online, 10 stale, 0 offline/conflicts/failed ingests; notifications pending=0/retrying=0. Это прежняя телеметрия парка; fleet readiness из этих counts не следует.
- Telegram: прежняя запись SENT, attempts=1, message_id=8, sent_at `2026-10-04T19:25:06.178269+00:00`. В `20:23:23` и `20:24:12 UTC` worker сообщил sent=0/retry_scheduled=0. Новое тестовое сообщение в этом UI-релизе не создавалось.
- Backup/restore/monitor/notifications timers active; monitor source/install byte comparison PASS.

Post-deployment encrypted R2 object: `assetguard-production-20261004-202450.sql.agbackup`. Upload завершён в `20:25:03 UTC`; при первой попытке R2 вернул 501, штатный второй retry завершился успешно. Isolated off-site restore PASS в `2026-10-04 20:27:17 UTC`: schema `0026`, assets=216, endpoints=11, service result success/inactive. Этот restore проверяет revision и основные counts; fingerprints всех строк и payload очереди отдельно не сравнивались.

## Известные границы и следующий этап

Это завершённый первый этап каркаса, а не модернизация всех пяти этапов. Следующий продуктовый этап: реестр/карточка имущества и единый центр технических/физических инцидентов (UX-04–07). Затем кабинеты/обход/импорт, Agent/admin и полная приёмка доступности и производительности. Исходное ТЗ и Vision logic сохраняются.

Fleet acceptance на 3–5 реальных ПК, unsigned installer `0.1.7`, приёмка нескольких школ и отдельный production inference host остаются самостоятельными задачами. Объекты Vision не входят в PostgreSQL backup.
