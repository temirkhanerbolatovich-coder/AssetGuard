# Наблюдаемость и аудит

С версии схемы `0026` новые инциденты отправляются отдельным worker через [durable Telegram queue](../features/telegram-notifications.md). `/admin/operations/status` показывает scoped `notifications.pending/retrying`. Monitor также проверяет failed notification job и ожидающие повтор сообщения; сообщения на русском, со временем UTC+5 и ссылкой. Сводная дедупликация не заменяет индивидуальные события Agent. Приёмка 2026-10-04 ниже относится к предыдущей версии; новая проверка записывается отдельно.

## Логируемые факты

- received/rejected inventory без секретов;
- normalizer errors и identity conflicts;
- snapshot creation;
- diff, event и incident creation;
- baseline acceptance/supersede;
- incident decision и resolve.
- Vision model load, scan start/completion, detection count и runtime errors без содержимого изображения.

## Не является диагностикой

Отсутствие telemetry по `LastSeenAt` может переводить endpoint в `REQUIRES_VERIFICATION` согласно настроенной policy. Оно не доказывает кражу, пропажу устройства или отсутствие железа. Аналогично Vision `WARNING` означает только расхождение counts с baseline.

На 2026-10-04 `/admin/operations/status` вычисляет freshness при чтении по `ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS` (24 часа по умолчанию). Старые `ONLINE` и `REQUIRES_VERIFICATION` попадают в `agents.stale` без вызова maintenance и без записи в БД. `OFFLINE` и `IDENTITY_CONFLICT` считаются отдельно; агрегаты ограничены организацией и разрешёнными кабинетами.

Monitor суммирует offline/stale, подавляет одинаковые проблемы на 4 часа и очищает fingerprint после здорового запуска. Если та же проблема возвращается после восстановления, alert отправляется сразу. Fingerprint сохраняется только после ответа Telegram `ok=true` с `message_id`; отказ не подавляет следующую попытку. Некорректные JSON metrics создают отдельную проблему. `--state-dir` позволяет использовать отдельное состояние в тестовом окружении; production default — `/var/lib/assetguard-monitor`.

Локальный тест `test_server_monitor.py` выполняет настоящий Bash script с подставными health/metrics/delivery и отдельными файлами состояния: stale → acceptance → dedup → recovery → recurrence → отказ → retry, а также malformed metrics. Версия из application commit `93ff8ed` установлена на production 2026-10-04; byte comparison с repository source прошёл. С разрешения пользователя отправлен один настоящий test alert: Telegram подтвердил `ok=true` с `message_id`, немедленный повтор подавлен. Проверка использовала отдельный `--state-dir`, сохранив текущее состояние обычных уведомлений. Production timer активен; recovery/refusal/retry проверены автоматическим тестом, реальный сбой API намеренно не создавался.

Read-only production acceptance 2026-10-04 показала: 11 endpoints, 1 online, 10 stale, 0 offline, 0 identity conflicts и 0 failed ingests. Stale отражает отсутствие свежей телеметрии тестовых ПК; успешная выкладка API не означает, что эти ПК прошли fleet acceptance. Точные результаты — в [release record](../../outputs/assetguard-release-2026-10-04.md).

## Операционные документы

Локальный запуск описан в `local-demo-guide.md`, PDF/OCR — в `pdf-import-ocr.md`, а HTTPS deployment, backup и restore — в `production-deployment.md`. Изолированная локальная репетиция восстановления прошла 2026-09-24. Windows daily backup и weekly rehearsal завершились с кодом `0` 2026-09-27. В тот же день постоянный сервер создал новую encrypted R2-копию и восстановил её в disposable PostgreSQL с результатом `PASS`: revision `0024_physical_asset_operations`, `assets=211`, `endpoints=1`. Server monitor запускается каждые 5 минут и проверяет readiness, Compose services, disk, возраст и failed jobs backup/restore, Agent last-seen, failed ingest и identity conflicts. Контролируемый test alert был принят Telegram, повторный запуск подавлен дедупликацией, normal run завершился без проблем. Неизменившийся alert повторяется через 4 часа; формальная on-call escalation остаётся организационной задачей.
