# Модель безопасности

## Область действия

Документ описывает меры, подтверждённые текущим backend, migrations, Compose, Caddy и тестами. Это модель MVP, а не заявление о пройденном внешнем аудите или соответствии стандарту.

## Защищаемые данные

- raw inventory и аппаратные идентификаторы endpoint;
- учётные записи, password hashes, session hashes и agent credentials;
- структура организаций и помещений, данные активов и ответственных лиц;
- incidents, решения, история и PDF-акты;
- изображения помещений и результаты Vision;
- backup archives и ключи их шифрования.

## Границы доверия

| Граница | Подтверждённая защита | Ограничение |
| --- | --- | --- |
| Internet → Caddy | HTTPS, HSTS, security headers, body limit 10 MB | Proxy-level rate limiting не настроен |
| Caddy → API | Внутренняя Docker-сеть | Трафик внутри сети Compose не шифруется |
| Browser → admin API | Named session либо bootstrap admin/viewer secret | Bootstrap secrets глобальны и не имеют индивидуальной атрибуции |
| Agent → ingestion | Per-agent HTTP Basic; legacy shared-secret fallback | Shared fallback увеличивает blast radius |
| API → PostgreSQL | Отдельная connection string из environment | Подтверждённого TLS для DB внутри Compose нет |
| API → Vision storage | Нормализованный storage root и generated scan IDs | Изображения требуют отдельной retention policy |
| Backup host → R2 | AGBK1 AES-256-GCM archive; account token ограничен одним backup bucket; Windows/Linux schedules и server alerting проверены | Vision volume не входит в PostgreSQL backup |

## Authentication

- Пароли named users хэшируются `PBKDF2-HMAC-SHA256` с индивидуальной 16-byte salt и 310 000 итераций.
- Session token создаётся криптографическим генератором; в PostgreSQL сохраняется только SHA-256 hash. Стандартный срок сессии — 12 часов.
- Сессия становится недействительной после expiry, отзыва или отключения пользователя.
- Admin API получает credential в `X-AssetGuard-Admin-Token`.
- Agent credentials хранятся в хэшированном виде. Для ротации поддержаны previous inventory/admin shared secrets.
- Re-enrolment после переустановки требует совпадения нормализованного SMBIOS UUID и решения `ADMIN`. Одноразовый claim token действует 30 минут: сервер хранит SHA-256 для lookup и PBKDF2 hash для нового Agent credential, но не plaintext.

MFA и SSO в коде отсутствуют. Re-enrolment восстанавливает только Agent credential и не является recovery для учётной записи администратора.

## Authorization

В коде используются роли `ADMIN`, `VIEWER`, `LOCATION_MANAGER` и `INVENTORY_CLERK`. Named principal содержит `organization_id`; tenant-scoped ресурсы фильтруются по нему. Для помещений предусмотрены grants `VIEWER` и `EDITOR`.

Смысл ролей подтверждается route dependencies, исполняемой allow/deny-матрицей всех 60 защищённых operations и tenant/location integration tests. Актуальная матрица находится в [admin-route-access-matrix.md](admin-route-access-matrix.md).

## Защита входных данных

- Inventory envelope валидируется по типам и обязательным полям.
- JSON inventory по умолчанию ограничен 2 MiB; Caddy ограничивает внешний request body 10 MB.
- Vision принимает только JPEG/PNG и применяет отдельный лимит 10 MiB по умолчанию.
- Rate limiter ограничивает защищённые route groups по client IP и первому сегменту пути, по умолчанию 120 запросов в минуту.
- SQL-доступ реализован через SQLAlchemy expressions; динамическая сборка пользовательского SQL в прикладных путях не используется.
- PDF/OCR import имеет отдельные проверки и тестовые сценарии, но остаётся обработкой недоверенного файла.

## Секреты и журналирование

Production secrets поступают из environment; Compose требует основные значения при запуске. `.env` не должен попадать в Git. CI сканирует полную историю Gitleaks и проверяет установленные Python dependencies через `pip-audit`.

Caddy удаляет `X-AssetGuard-Admin-Token`, `Authorization` и `Cookie` из access logs. Application logs фиксируют path, status, duration и доменные identifiers, но не должны включать payload, пароль или token.

## Данные и восстановление

Raw inventory и исторические записи используются как audit evidence. Database migrations добавляют ограничения неизменяемости для критичных записей. Production volumes сохраняют PostgreSQL, Vision images и model cache вне жизненного цикла контейнера.

Backup scripts поддерживают шифрование AES-256-GCM и restore rehearsal. Ключ backup хранится отдельно от архива: на Windows-контуре — в DPAPI-хранилище текущего пользователя, на Linux-сервере — в root-only configuration. Upload, повторное скачивание и восстановление свежей копии из Cloudflare R2 успешно выполнены 2026-09-27 через Windows Task Scheduler и постоянный server systemd. Server monitor проверяет возраст копии и failed backup/restore jobs; test alert был принят Telegram, второй запуск подавлен дедупликацией. Vision image volume в PostgreSQL backup не входит.

## Проверки

- `test_auth_lifecycle.py` — login, sessions и revoke;
- `test_tenant_isolation.py` — разделение организаций;
- `test_location_scoped_resources.py` — доступ к помещениям;
- `test_native_glpi_transport.py` — agent transport authentication;
- `test_agent_reenrolment.py` — claim token, admin approval, автоматический revoke и сохранение endpoint;
- `test_privacy_profile_fixture.py` — минимальный профиль собираемых данных;
- `test_backup_crypto_interop.py` — совместимость backup crypto;
- GitHub Actions — Gitleaks и `pip-audit`.

## Известные риски

Приоритетный незакрытый security/operations debt: отказ от общих bootstrap/agent secrets, формальная retention policy и дальнейшая проверка production hardening. Он ведётся в [technical-debt.md](../technical-debt.md).
