# Наблюдаемость и аудит

## Логируемые факты

- received/rejected inventory без секретов;
- normalizer errors и identity conflicts;
- snapshot creation;
- diff, event и incident creation;
- baseline acceptance/supersede;
- incident decision и resolve.

## Не является диагностикой

Отсутствие telemetry по `LastSeenAt` может переводить endpoint в `REQUIRES_VERIFICATION` согласно будущей policy. Оно не доказывает кражу, пропажу устройства или отсутствие железа.

## Будущие операционные документы

До первого развёртывания потребуются политика backup/restore, retention, incident response и описание локальной/development среды.

