# Минимальная security baseline MVP

## Обязательные меры

- HTTPS и нормальная проверка сертификата для GLPI Agent;
- аутентификация и авторизация admin API/UI;
- secrets вне исходного кода и логов;
- ограничение размера payload, schema validation и basic rate limiting;
- audit важный административных действий;
- отсутствие публичного доступа к PostgreSQL.

## Запреты

- `NO_SSL_CHECK` в production;
- логирование секретов, токенов и полных чувствительных payload без необходимости;
- использование внутренней БД GLPI как базы AssetGuard.

## До реализации

Нужно отдельно определить trust boundary для ingest endpoint, ротацию ключей/секретов, роли администратора и retention raw payload.

