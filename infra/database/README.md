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

Миграции будут добавлены вместе с первой доменной схемой; schema creation в runtime приложения не допускается.

