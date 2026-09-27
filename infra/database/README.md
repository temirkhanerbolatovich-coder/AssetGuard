# PostgreSQL for AssetGuard

PostgreSQL является единственной operational database AssetGuard. В production порт БД не должен быть опубликован наружу; Compose для локальной разработки привязывает его только к `127.0.0.1`.

Перед запуском создайте локальный `.env` из корневого `.env.example` и добавьте:

```dotenv
ASSETGUARD_POSTGRES_DB=assetguard
ASSETGUARD_POSTGRES_USER=assetguard
ASSETGUARD_POSTGRES_PASSWORD=<локальный-секрет>
ASSETGUARD_POSTGRES_PORT=5432
```

Запуск, когда Docker Desktop daemon доступен:

```powershell
docker compose --env-file .env -f infra/containers/docker-compose.yml up -d postgres
```

Alembic — единственный поддерживаемый механизм изменения схемы. Текущий `head` — `0025_agent_reenrolment`; schema creation через `Base.metadata.create_all()` в runtime приложения не допускается.

Проверка и применение выполняются из `backend`:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m alembic heads
.\.venv\Scripts\python.exe -m alembic upgrade head
Pop-Location
```

Перед production migration создайте свежий encrypted backup и проверьте readiness после обновления. Не используйте production connection string для тестов: pytest создаёт и удаляет отдельную database.
