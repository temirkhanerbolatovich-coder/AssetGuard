# Наблюдаемость и аудит

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

Локальный тест `test_server_monitor.py` выполняет настоящий Bash script с подставными health/metrics/delivery и отдельными файлами состояния: stale → acceptance → dedup → recovery → recurrence → отказ → retry, а также malformed metrics. Это проверка логики; новая версия ещё не развёрнута и фактическая доставка пользователю на production в этом прогоне не проверялась.

## Операционные документы

Локальный запуск описан в `local-demo-guide.md`, PDF/OCR — в `pdf-import-ocr.md`, а HTTPS deployment, backup и restore — в `production-deployment.md`. Изолированная локальная репетиция восстановления прошла 2026-09-24. Windows daily backup и weekly rehearsal завершились с кодом `0` 2026-09-27. В тот же день постоянный сервер создал новую encrypted R2-копию и восстановил её в disposable PostgreSQL с результатом `PASS`: revision `0024_physical_asset_operations`, `assets=211`, `endpoints=1`. Server monitor запускается каждые 5 минут и проверяет readiness, Compose services, disk, возраст и failed jobs backup/restore, Agent last-seen, failed ingest и identity conflicts. Контролируемый test alert был принят Telegram, повторный запуск подавлен дедупликацией, normal run завершился без проблем. Неизменившийся alert повторяется через 4 часа; формальная on-call escalation остаётся организационной задачей.
