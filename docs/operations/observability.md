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

## Операционные документы

Локальный запуск описан в `local-demo-guide.md`, PDF/OCR — в `pdf-import-ocr.md`, а HTTPS deployment, backup и restore — в `production-deployment.md`. Изолированная локальная репетиция восстановления зашифрованной копии успешно прошла 2026-09-24. Постоянный Oracle Cloud deployment, DuckDNS, TLS и health/readiness проверены 2026-09-25. Локальный Windows monitor умеет отправлять дедуплицированные Telegram-alerts по offline Agent, failed ingest, identity conflicts и месту на диске. До production-пилота остаются off-host encrypted backup с восстановлением именно из внешней копии и перенос мониторинга в постоянный серверный контур.
