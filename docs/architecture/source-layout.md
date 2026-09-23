# Карта будущей структуры исходного кода

Структура ориентирована на modular monolith. Каждый модуль инкапсулирует прикладную логику и не требует самостоятельного развёртывания.

```text
backend/
  src/
    assetguard/
      modules/
        assets/          # Asset, Organization, связь Asset—Endpoint
        endpoints/       # ManagedEndpoint и идентификаторы
        inventory/       # Gateway, RawInventory, source adapters
        snapshots/       # normalizer и HardwareSnapshot
        baselines/       # явное принятие и supersede baseline
        changes/         # diff, evidence, deterministic deduplication
        incidents/       # workflow и append-only decisions
        history/         # единая append-only timeline
        identity/        # canonicalization, confidence, component matching
      shared/            # минимальные общие типы, ошибки, время, audit
      interfaces/        # HTTP/admin входы и контракты
      infrastructure/    # PostgreSQL, внешние API, logging
  tests/
    unit/
    integration/
    contract/
    fixtures/
frontend/
  src/
    features/            # dashboard, assets, incidents
    shared/
infra/
  database/              # будущие миграции и локальная БД
  containers/            # будущие compose/container definition
  observability/         # будущая конфигурация logs/metrics
```

Каталоги созданы как пустой каркас. Выбор языка, фреймворка, ORM и конкретных файлов делается отдельным решением после утверждения implementation plan и результатов spike.

