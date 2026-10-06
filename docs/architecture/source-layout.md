# Фактическая структура исходного кода

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Проект остаётся FastAPI modular monolith: доменные модули разделены в коде, но используют единый API process и PostgreSQL.

```text
backend/
  migrations/versions/       # Alembic migrations 0001–0026
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
      identity/               # users, sessions, roles, Agent credentials и re-enrolment
      notifications/          # transactional Telegram outbox и bounded worker
      vision/                 # detection, annotation, counts и room baseline
  tests/
    fixtures/                 # sanitized GLPI Agent payloads
    unit/                     # normalization/privacy/health tests
    integration/              # inventory, auth, tenant, Agent lifecycle и Vision vertical slices
    e2e/                      # Chromium-сценарии Dashboard
frontend/                     # единый HTML/CSS/JS Dashboard
infra/containers/             # local PostgreSQL и production Compose/Caddy
scripts/windows/              # local run, Agent SYSTEM task/FIFO, installer/lifecycle, fleet checks, backup/restore
scripts/linux/                # production backup, restore rehearsal, monitoring и notification worker
demo/vision/                  # воспроизводимая пара demo-изображений
docs/                         # architecture, API, product и operations
```

Vision намеренно не вынесен в отдельный service для demo MVP. Модель загружается лениво, поэтому обычный inventory workflow не зависит от её инициализации. Отдельный inference service и object storage остаются production evolution, а не требованием текущей архитектуры.
