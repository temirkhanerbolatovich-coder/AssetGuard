# Фактическая структура исходного кода

Проект остаётся FastAPI modular monolith: доменные модули разделены в коде, но используют единый API process и PostgreSQL.

```text
backend/
  migrations/versions/       # Alembic migrations 0001–0009
  src/assetguard/
    app.py                    # HTTP composition root и static Dashboard
    infrastructure/           # config, database, HTTP middleware
    interfaces/http/          # inventory, admin, auth и Vision routers
    modules/
      assets/                 # Asset и связь Asset—Endpoint
      endpoints/              # endpoint status/identity operations
      inventory/              # RawInventory, envelope schema, source adapter boundary и ingestion workflow
      snapshots/              # hardware normalization
      baselines/              # explicit hardware baseline
      changes/                # evidence-aware diff и deduplication
      incidents/              # incident workflow
      history/                # append-only Asset timeline
      identity/               # users, sessions и authentication
      vision/                 # detection, annotation, counts и room baseline
  tests/
    fixtures/                 # sanitized GLPI Agent payloads
    unit/                     # normalization/privacy/health tests
    integration/              # inventory и Vision vertical slices
frontend/                     # единый HTML/CSS/JS Dashboard
infra/containers/             # local PostgreSQL и production Compose/Caddy
scripts/windows/              # local run, collection, scheduled tasks, backup/restore
demo/vision/                  # воспроизводимая пара demo-изображений
docs/                         # architecture, API, product и operations
```

Vision намеренно не вынесен в отдельный service для demo MVP. Модель загружается лениво, поэтому обычный inventory workflow не зависит от её инициализации. Отдельный inference service остаётся возможным production evolution, а не требованием текущей архитектуры.
