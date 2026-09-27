# Минимальная security baseline MVP

## Обязательные меры

- HTTPS и нормальная проверка сертификата для GLPI Agent;
- аутентификация и авторизация admin API/UI;
- secrets вне исходного кода и логов;
- единый лимит входящего payload 10 MB на Caddy и API, schema validation и basic rate limiting;
- audit важных административных действий;
- отсутствие публичного доступа к PostgreSQL.

## Запреты

- `NO_SSL_CHECK` в production;
- логирование секретов, токенов и полных чувствительных payload без необходимости;
- использование внутренней БД GLPI как базы AssetGuard.

## Реализовано

- ingest отделён в `/internal` boundary с отдельным rotating shared secret;
- Named `ADMIN`, `VIEWER`, `LOCATION_MANAGER` и `INVENTORY_CLERK` users используют revocable 12-hour sessions;
- Каждый новый Agent получает отдельный credential; одобряемое re-enrolment хранит claim token только как hashes и отзывает прежний активный ключ;
- Location grants на корпус/этаж/кабинет разграничивают чтение и редактирование на API boundary; allow/deny-матрица покрывает все 60 admin operations, а перед multi-school rollout остаётся реальная приёмка двух организаций;
- logout, административный revoke, disable user и password rotation отзывают активные sessions;
- actor административного incident decision выводится из authenticated principal;
- `/auth/login`, `/admin` и `/internal` защищены базовым rate limit;
- Caddy удаляет custom admin token, `Authorization` и `Cookie` из runtime-логов до их записи;
- raw evidence и audit history защищены append-only database triggers.

Постоянный Oracle Cloud deployment с публичным TLS endpoint принят 2026-09-25. Автоматический secret scan всей Git-истории и локальный pre-commit hook включены. Encrypted upload, download и isolated restore свежей Cloudflare R2-копии успешно выполнены 2026-09-27 с bucket-scoped account token через Windows tasks и Linux systemd; server services вернули `Result=success`. Telegram test alert принят, повторный запуск подавлен дедупликацией. До расширения пилота остаются внешний proxy-level rate limit, SAST/container scanning, MFA/SSO, code signing Agent и утверждённая retention policy для raw inventory и Vision images.
