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

## Реализовано

- ingest отделён в `/internal` boundary с отдельным rotating shared secret;
- Named `ADMIN`, `VIEWER`, `LOCATION_MANAGER` и `INVENTORY_CLERK` users используют revocable 12-hour sessions;
- Location grants на корпус/этаж/кабинет разграничивают чтение и редактирование активов/отчётов на API boundary; расширенная tenant-route matrix ещё нужна до multi-school rollout;
- logout, административный revoke, disable user и password rotation отзывают активные sessions;
- actor административного incident decision выводится из authenticated principal;
- `/auth/login`, `/admin` и `/internal` защищены базовым rate limit;
- raw evidence и audit history защищены append-only database triggers.

До production остаются внешний proxy-level rate limit, deployment acceptance на целевом хосте, encrypted off-host backup, репетиция восстановления из off-site копии и утверждённая retention policy для Vision images. Локальная изолированная репетиция восстановления encrypted backup успешно выполнена 2026-09-24; это подтверждает процедуру восстановления, но не заменяет внешний backup.
