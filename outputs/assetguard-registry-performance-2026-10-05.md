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

Локально **125 passed**: 109 unit/integration и 16 browser E2E. `node --check frontend/app.js` и `git diff --check` прошли. Обновлены методика UI-приёмки, testing strategy и changelog. Результаты CI и серверной приёмки добавляются после завершения проверок. До этого production остаётся на предыдущем приложении.
