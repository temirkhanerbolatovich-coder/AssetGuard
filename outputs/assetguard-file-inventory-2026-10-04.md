# AssetGuard: инвентаризация файлов

> **Исторический документ.** Даты, SHA, измерения и исходные требования ниже относятся к описанному этапу. Сверка указателя выполнена 2026-10-06; текущее состояние и оставшаяся работа — в [checklist](../docs/product/current-project-checklist.md) и [аудите](../docs/quality/project-audit-2026-10-06.md).

Дата: 4 октября 2026 года. HEAD: `2b441fb756bd066b234e537357874426cc6f3b05`.

Всего 241 отслеживаемый файл. GitHub recursive tree для HEAD также содержит 241 файл и не усечён. Это перечень scope и выполненных типов проверки; он не означает построчную ручную проверку каждой строки или исполнение каждого скрипта.

[Основной отчёт и план](assetguard-audit-2026-10-04.md)

| Файл | Размер, bytes | Строки | Область | Проверка / граница |
| --- | ---: | ---: | --- | --- |
| [.dockerignore](../.dockerignore) | 74 | 7 | Repository configuration | Inventory/role inspection |
| [.env.example](../.env.example) | 1739 | 31 | Repository configuration | Inventory/role inspection |
| [.github/dependabot.yml](../.github/dependabot.yml) | 264 | 12 | CI/dependencies | Configuration/source inspection; no current deployment/build |
| [.github/workflows/ci.yml](../.github/workflows/ci.yml) | 4972 | 132 | CI/dependencies | Configuration/source inspection; no current deployment/build |
| [.gitignore](../.gitignore) | 460 | 37 | Repository configuration | Inventory/role inspection |
| [.pre-commit-config.yaml](../.pre-commit-config.yaml) | 103 | 5 | Repository configuration | Configuration/source inspection; no current deployment/build |
| [ASSETGUARD_MVP_v0.1_ANALYSIS.md](../ASSETGUARD_MVP_v0.1_ANALYSIS.md) | 6217 | 76 | Requirements/status/research | Relative links PASS; context/status review |
| [ASSETGUARD_MVP_v0.1_REQUIREMENTS.md](../ASSETGUARD_MVP_v0.1_REQUIREMENTS.md) | 17723 | 276 | Requirements/status/research | Relative links PASS; context/status review |
| [ASSETGUARD_TECHNICAL_RESEARCH.md](../ASSETGUARD_TECHNICAL_RESEARCH.md) | 44526 | 623 | Requirements/status/research | Relative links PASS; context/status review |
| [CHANGELOG.md](../CHANGELOG.md) | 2557 | 40 | Requirements/status/research | Relative links PASS; context/status review |
| [README.md](../README.md) | 9587 | 132 | Requirements/status/research | Relative links PASS; context/status review |
| [backend/.gitkeep](../backend/.gitkeep) | 1 | 1 | Repository configuration | Reserved directory; no behavior |
| [backend/Dockerfile](../backend/Dockerfile) | 864 | 17 | Repository configuration | Configuration/source inspection; no current deployment/build |
| [backend/README.md](../backend/README.md) | 9337 | 67 | Requirements/status/research | Relative links PASS; context/status review |
| [backend/alembic.ini](../backend/alembic.ini) | 612 | 37 | Repository configuration | Inventory/role inspection |
| [backend/migrations/env.py](../backend/migrations/env.py) | 1421 | 57 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/script.py.mako](../backend/migrations/script.py.mako) | 622 | 27 | Migration/config | Inventory/role inspection |
| [backend/migrations/versions/0001_raw_inventories.py](../backend/migrations/versions/0001_raw_inventories.py) | 3807 | 107 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0002_raw_inventory_idempotency.py](../backend/migrations/versions/0002_raw_inventory_idempotency.py) | 873 | 37 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0003_endpoints_and_hardware_snapshots.py](../backend/migrations/versions/0003_endpoints_and_hardware_snapshots.py) | 7467 | 132 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0004_baselines_changes.py](../backend/migrations/versions/0004_baselines_changes.py) | 4405 | 69 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0005_incidents_history.py](../backend/migrations/versions/0005_incidents_history.py) | 3980 | 27 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0006_assets.py](../backend/migrations/versions/0006_assets.py) | 2243 | 23 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0007_complete_mvp_foundation.py](../backend/migrations/versions/0007_complete_mvp_foundation.py) | 3617 | 72 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0008_users_and_sessions.py](../backend/migrations/versions/0008_users_and_sessions.py) | 1975 | 46 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0009_vision_mvp.py](../backend/migrations/versions/0009_vision_mvp.py) | 3769 | 74 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0010_asset_locations.py](../backend/migrations/versions/0010_asset_locations.py) | 570 | 23 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0011_vision_asset_link.py](../backend/migrations/versions/0011_vision_asset_link.py) | 903 | 26 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0012_agent_credentials.py](../backend/migrations/versions/0012_agent_credentials.py) | 1418 | 33 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0013_tenant_foundation.py](../backend/migrations/versions/0013_tenant_foundation.py) | 1168 | 25 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0014_endpoint_tenant_scope.py](../backend/migrations/versions/0014_endpoint_tenant_scope.py) | 918 | 22 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0015_vision_tenant_scope.py](../backend/migrations/versions/0015_vision_tenant_scope.py) | 1142 | 22 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0016_location_hierarchy.py](../backend/migrations/versions/0016_location_hierarchy.py) | 4842 | 57 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0017_asset_accounting_modes.py](../backend/migrations/versions/0017_asset_accounting_modes.py) | 2163 | 40 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0018_classify_imported_property.py](../backend/migrations/versions/0018_classify_imported_property.py) | 1454 | 33 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0019_location_access.py](../backend/migrations/versions/0019_location_access.py) | 1270 | 22 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0020_expanded_user_roles.py](../backend/migrations/versions/0020_expanded_user_roles.py) | 724 | 29 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0021_vision_location_scope.py](../backend/migrations/versions/0021_vision_location_scope.py) | 1848 | 51 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0022_room_physical_inspections.py](../backend/migrations/versions/0022_room_physical_inspections.py) | 3804 | 72 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0023_physical_incident_workflow.py](../backend/migrations/versions/0023_physical_incident_workflow.py) | 4459 | 83 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0024_physical_asset_operations.py](../backend/migrations/versions/0024_physical_asset_operations.py) | 2424 | 36 | Migration/config | AST PASS; selected behavior review |
| [backend/migrations/versions/0025_agent_reenrolment.py](../backend/migrations/versions/0025_agent_reenrolment.py) | 3524 | 67 | Migration/config | AST PASS; selected behavior review |
| [backend/pyproject.toml](../backend/pyproject.toml) | 994 | 48 | Repository configuration | Configuration/source inspection; no current deployment/build |
| [backend/scripts/vision_local_demo_http_test.py](../backend/scripts/vision_local_demo_http_test.py) | 2569 | 44 | Vision runtime check | AST PASS; selected behavior review |
| [backend/scripts/vision_real_model_smoke.py](../backend/scripts/vision_real_model_smoke.py) | 1108 | 30 | Vision runtime check | AST PASS; selected behavior review |
| [backend/src/.gitkeep](../backend/src/.gitkeep) | 1 | 1 | Repository configuration | Reserved directory; no behavior |
| [backend/src/assetguard/__init__.py](../backend/src/assetguard/__init__.py) | 44 | 2 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/app.py](../backend/src/assetguard/app.py) | 1957 | 42 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/infrastructure/.gitkeep](../backend/src/assetguard/infrastructure/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/infrastructure/config.py](../backend/src/assetguard/infrastructure/config.py) | 4514 | 94 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/infrastructure/database.py](../backend/src/assetguard/infrastructure/database.py) | 725 | 25 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/infrastructure/http_middleware.py](../backend/src/assetguard/infrastructure/http_middleware.py) | 2468 | 57 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/.gitkeep](../backend/src/assetguard/interfaces/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/interfaces/http/__init__.py](../backend/src/assetguard/interfaces/http/__init__.py) | 37 | 2 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/admin_assets.py](../backend/src/assetguard/interfaces/http/admin_assets.py) | 57798 | 1028 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/admin_inventories.py](../backend/src/assetguard/interfaces/http/admin_inventories.py) | 3256 | 71 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/admin_locations.py](../backend/src/assetguard/interfaces/http/admin_locations.py) | 44230 | 694 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/admin_workflows.py](../backend/src/assetguard/interfaces/http/admin_workflows.py) | 11756 | 229 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/auth.py](../backend/src/assetguard/interfaces/http/auth.py) | 16951 | 331 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/authorization.py](../backend/src/assetguard/interfaces/http/authorization.py) | 2616 | 81 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/glpi_agent.py](../backend/src/assetguard/interfaces/http/glpi_agent.py) | 5420 | 106 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/health.py](../backend/src/assetguard/interfaces/http/health.py) | 4998 | 104 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/inventories.py](../backend/src/assetguard/interfaces/http/inventories.py) | 4885 | 121 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/pdf_support.py](../backend/src/assetguard/interfaces/http/pdf_support.py) | 752 | 20 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/resource_scope.py](../backend/src/assetguard/interfaces/http/resource_scope.py) | 1198 | 30 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/interfaces/http/vision.py](../backend/src/assetguard/interfaces/http/vision.py) | 9310 | 190 | Backend: HTTP | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/assets/.gitkeep](../backend/src/assetguard/modules/assets/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/assets/models.py](../backend/src/assetguard/modules/assets/models.py) | 5595 | 147 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/baselines/.gitkeep](../backend/src/assetguard/modules/baselines/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/baselines/models.py](../backend/src/assetguard/modules/baselines/models.py) | 981 | 28 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/baselines/service.py](../backend/src/assetguard/modules/baselines/service.py) | 1941 | 48 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/changes/.gitkeep](../backend/src/assetguard/modules/changes/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/changes/detector.py](../backend/src/assetguard/modules/changes/detector.py) | 8949 | 194 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/changes/models.py](../backend/src/assetguard/modules/changes/models.py) | 1689 | 44 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/endpoints/.gitkeep](../backend/src/assetguard/modules/endpoints/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/endpoints/service.py](../backend/src/assetguard/modules/endpoints/service.py) | 1220 | 27 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/history/.gitkeep](../backend/src/assetguard/modules/history/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/history/service.py](../backend/src/assetguard/modules/history/service.py) | 1931 | 46 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/identity/.gitkeep](../backend/src/assetguard/modules/identity/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/identity/auth.py](../backend/src/assetguard/modules/identity/auth.py) | 2808 | 86 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/identity/location_access.py](../backend/src/assetguard/modules/identity/location_access.py) | 1981 | 34 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/identity/models.py](../backend/src/assetguard/modules/identity/models.py) | 4331 | 78 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/incidents/.gitkeep](../backend/src/assetguard/modules/incidents/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/incidents/models.py](../backend/src/assetguard/modules/incidents/models.py) | 5163 | 91 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/incidents/service.py](../backend/src/assetguard/modules/incidents/service.py) | 2987 | 65 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/inventory/.gitkeep](../backend/src/assetguard/modules/inventory/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/inventory/adapters.py](../backend/src/assetguard/modules/inventory/adapters.py) | 4371 | 112 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/inventory/models.py](../backend/src/assetguard/modules/inventory/models.py) | 1669 | 41 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/inventory/raw_inventory.py](../backend/src/assetguard/modules/inventory/raw_inventory.py) | 933 | 34 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/inventory/schema.py](../backend/src/assetguard/modules/inventory/schema.py) | 1080 | 28 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/inventory/service.py](../backend/src/assetguard/modules/inventory/service.py) | 2121 | 67 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/snapshots/.gitkeep](../backend/src/assetguard/modules/snapshots/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/src/assetguard/modules/snapshots/models.py](../backend/src/assetguard/modules/snapshots/models.py) | 4448 | 108 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/snapshots/normalizer.py](../backend/src/assetguard/modules/snapshots/normalizer.py) | 13669 | 277 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/vision/detector.py](../backend/src/assetguard/modules/vision/detector.py) | 2743 | 71 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/vision/models.py](../backend/src/assetguard/modules/vision/models.py) | 2822 | 55 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/modules/vision/service.py](../backend/src/assetguard/modules/vision/service.py) | 8167 | 161 | Backend: domain/infrastructure | AST PASS; selected behavior review |
| [backend/src/assetguard/shared/.gitkeep](../backend/src/assetguard/shared/.gitkeep) | 1 | 1 | Backend: domain/infrastructure | Reserved directory; no behavior |
| [backend/tests/conftest.py](../backend/tests/conftest.py) | 2941 | 75 | Automated test | AST PASS; selected behavior review |
| [backend/tests/contract/.gitkeep](../backend/tests/contract/.gitkeep) | 1 | 1 | Automated test | Reserved directory; no behavior |
| [backend/tests/e2e/test_dashboard.py](../backend/tests/e2e/test_dashboard.py) | 28025 | 470 | Automated test | AST PASS; selected behavior review |
| [backend/tests/fixtures/.gitkeep](../backend/tests/fixtures/.gitkeep) | 1 | 1 | Sanitized test fixture | Reserved directory; no behavior |
| [backend/tests/fixtures/glpi-agent-full-sanitized.json](../backend/tests/fixtures/glpi-agent-full-sanitized.json) | 481 | 25 | Sanitized test fixture | Inventory/role inspection |
| [backend/tests/fixtures/glpi-agent-hardware-ram-removed.json](../backend/tests/fixtures/glpi-agent-hardware-ram-removed.json) | 377 | 10 | Sanitized test fixture | Inventory/role inspection |
| [backend/tests/fixtures/glpi-agent-hardware-ssd-replaced.json](../backend/tests/fixtures/glpi-agent-hardware-ssd-replaced.json) | 477 | 13 | Sanitized test fixture | Inventory/role inspection |
| [backend/tests/fixtures/glpi-agent-hostname-changed.json](../backend/tests/fixtures/glpi-agent-hostname-changed.json) | 483 | 13 | Sanitized test fixture | Inventory/role inspection |
| [backend/tests/fixtures/glpi-agent-minimal-sanitized.json](../backend/tests/fixtures/glpi-agent-minimal-sanitized.json) | 674 | 17 | Sanitized test fixture | Inventory/role inspection |
| [backend/tests/fixtures/glpi-agent-partial-software-sanitized.json](../backend/tests/fixtures/glpi-agent-partial-software-sanitized.json) | 167 | 6 | Sanitized test fixture | Inventory/role inspection |
| [backend/tests/integration/.gitkeep](../backend/tests/integration/.gitkeep) | 1 | 1 | Automated test | Reserved directory; no behavior |
| [backend/tests/integration/test_agent_reenrolment.py](../backend/tests/integration/test_agent_reenrolment.py) | 8021 | 160 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_auth_lifecycle.py](../backend/tests/integration/test_auth_lifecycle.py) | 3246 | 64 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_endpoint_identity.py](../backend/tests/integration/test_endpoint_identity.py) | 3327 | 70 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_location_scoped_resources.py](../backend/tests/integration/test_location_scoped_resources.py) | 15579 | 257 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_mvp_workflow.py](../backend/tests/integration/test_mvp_workflow.py) | 25575 | 401 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_native_glpi_transport.py](../backend/tests/integration/test_native_glpi_transport.py) | 4628 | 84 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_raw_inventory_ingest.py](../backend/tests/integration/test_raw_inventory_ingest.py) | 1831 | 48 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_tenant_isolation.py](../backend/tests/integration/test_tenant_isolation.py) | 11498 | 154 | Automated test | AST PASS; selected behavior review |
| [backend/tests/integration/test_vision_workflow.py](../backend/tests/integration/test_vision_workflow.py) | 5304 | 131 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/.gitkeep](../backend/tests/unit/.gitkeep) | 1 | 1 | Automated test | Reserved directory; no behavior |
| [backend/tests/unit/test_admin_asset_units.py](../backend/tests/unit/test_admin_asset_units.py) | 296 | 7 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_admin_route_contract.py](../backend/tests/unit/test_admin_route_contract.py) | 8464 | 216 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_agent_version_reporting.py](../backend/tests/unit/test_agent_version_reporting.py) | 758 | 19 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_backup_crypto_interop.py](../backend/tests/unit/test_backup_crypto_interop.py) | 2459 | 61 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_health.py](../backend/tests/unit/test_health.py) | 1358 | 46 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_inventory_schema.py](../backend/tests/unit/test_inventory_schema.py) | 560 | 17 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_normalizer.py](../backend/tests/unit/test_normalizer.py) | 385 | 10 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_pdf_import.py](../backend/tests/unit/test_pdf_import.py) | 7661 | 147 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_privacy_profile_fixture.py](../backend/tests/unit/test_privacy_profile_fixture.py) | 635 | 23 | Automated test | AST PASS; selected behavior review |
| [backend/tests/unit/test_raw_inventory.py](../backend/tests/unit/test_raw_inventory.py) | 577 | 16 | Automated test | AST PASS; selected behavior review |
| [demo/vision/README.md](../demo/vision/README.md) | 784 | 9 | Vision demo artifact | Relative links PASS; context/status review |
| [demo/vision/room-305-baseline.png](../demo/vision/room-305-baseline.png) | 2354771 | binary | Vision demo artifact | Artifact inventory; no runtime/accuracy acceptance |
| [demo/vision/room-305-warning.png](../demo/vision/room-305-warning.png) | 2177258 | binary | Vision demo artifact | Artifact inventory; no runtime/accuracy acceptance |
| [docs/README.md](../docs/README.md) | 6076 | 54 | Project documentation | Relative links PASS; context/status review |
| [docs/api/README.md](../docs/api/README.md) | 7371 | 43 | Project documentation | Relative links PASS; context/status review |
| [docs/architecture/assetguard-vision-integration-analysis.md](../docs/architecture/assetguard-vision-integration-analysis.md) | 3582 | 35 | Project documentation | Relative links PASS; context/status review |
| [docs/architecture/data-flow.md](../docs/architecture/data-flow.md) | 7858 | 106 | Project documentation | Relative links PASS; context/status review |
| [docs/architecture/module-boundaries.md](../docs/architecture/module-boundaries.md) | 2106 | 16 | Project documentation | Relative links PASS; context/status review |
| [docs/architecture/overview.md](../docs/architecture/overview.md) | 6410 | 71 | Project documentation | Relative links PASS; context/status review |
| [docs/architecture/source-layout.md](../docs/architecture/source-layout.md) | 2540 | 36 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/ADR-001-modular-monolith.md](../docs/decisions/ADR-001-modular-monolith.md) | 1153 | 20 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/ADR-002-baseline-and-evidence.md](../docs/decisions/ADR-002-baseline-and-evidence.md) | 928 | 15 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/ADR-003-glpi-source-boundary.md](../docs/decisions/ADR-003-glpi-source-boundary.md) | 932 | 18 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/ADR-004-backend-stack.md](../docs/decisions/ADR-004-backend-stack.md) | 1286 | 20 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/ADR-005-agent-reenrolment.md](../docs/decisions/ADR-005-agent-reenrolment.md) | 5298 | 47 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/ADR-TEMPLATE.md](../docs/decisions/ADR-TEMPLATE.md) | 1476 | 38 | Project documentation | Relative links PASS; context/status review |
| [docs/decisions/README.md](../docs/decisions/README.md) | 2252 | 27 | Project documentation | Relative links PASS; context/status review |
| [docs/deployment/README.md](../docs/deployment/README.md) | 2917 | 27 | Project documentation | Relative links PASS; context/status review |
| [docs/domain/glossary.md](../docs/domain/glossary.md) | 3350 | 34 | Project documentation | Relative links PASS; context/status review |
| [docs/features/README.md](../docs/features/README.md) | 2107 | 17 | Project documentation | Relative links PASS; context/status review |
| [docs/integration/glpi-agent-minimal-profile-spike.md](../docs/integration/glpi-agent-minimal-profile-spike.md) | 2053 | 29 | Project documentation | Relative links PASS; context/status review |
| [docs/integration/glpi-agent-spike.md](../docs/integration/glpi-agent-spike.md) | 3279 | 42 | Project documentation | Relative links PASS; context/status review |
| [docs/integration/glpi-agent-transport-decision.md](../docs/integration/glpi-agent-transport-decision.md) | 2024 | 20 | Project documentation | Relative links PASS; context/status review |
| [docs/integration/glpi-agent-version-lock.md](../docs/integration/glpi-agent-version-lock.md) | 2655 | 30 | Project documentation | Relative links PASS; context/status review |
| [docs/integration/phase0-local-inventory-observation.md](../docs/integration/phase0-local-inventory-observation.md) | 3226 | 39 | Project documentation | Relative links PASS; context/status review |
| [docs/operations/agent-fleet-pilot.md](../docs/operations/agent-fleet-pilot.md) | 4433 | 39 | Project documentation | Relative links PASS; context/status review |
| [docs/operations/free-deployment.md](../docs/operations/free-deployment.md) | 5506 | 81 | Project documentation | Relative links PASS; context/status review |
| [docs/operations/local-demo-guide.md](../docs/operations/local-demo-guide.md) | 7524 | 57 | Project documentation | Relative links PASS; context/status review |
| [docs/operations/observability.md](../docs/operations/observability.md) | 2220 | 19 | Project documentation | Relative links PASS; context/status review |
| [docs/operations/pdf-import-ocr.md](../docs/operations/pdf-import-ocr.md) | 8333 | 57 | Project documentation | Relative links PASS; context/status review |
| [docs/operations/production-deployment.md](../docs/operations/production-deployment.md) | 10606 | 151 | Project documentation | Relative links PASS; context/status review |
| [docs/product/assetguard-vision-requirements.md](../docs/product/assetguard-vision-requirements.md) | 6448 | 53 | Project documentation | Relative links PASS; context/status review |
| [docs/product/current-project-checklist.md](../docs/product/current-project-checklist.md) | 25029 | 217 | Project documentation | Relative links PASS; context/status review |
| [docs/product/dashboard-data-audit.md](../docs/product/dashboard-data-audit.md) | 4576 | 39 | Project documentation | Relative links PASS; context/status review |
| [docs/product/demo-scenario.md](../docs/product/demo-scenario.md) | 1560 | 18 | Project documentation | Relative links PASS; context/status review |
| [docs/product/frontend-redesign-audit.md](../docs/product/frontend-redesign-audit.md) | 12457 | 149 | Project documentation | Relative links PASS; context/status review |
| [docs/product/inventory-operating-model.md](../docs/product/inventory-operating-model.md) | 5952 | 29 | Project documentation | Relative links PASS; context/status review |
| [docs/product/mvp-completion-checklist.md](../docs/product/mvp-completion-checklist.md) | 10423 | 79 | Project documentation | Relative links PASS; context/status review |
| [docs/product/pilot-release-plan.md](../docs/product/pilot-release-plan.md) | 3904 | 33 | Project documentation | Relative links PASS; context/status review |
| [docs/product/pitch-guide.md](../docs/product/pitch-guide.md) | 10849 | 127 | Project documentation | Relative links PASS; context/status review |
| [docs/product/production-readiness-roadmap.md](../docs/product/production-readiness-roadmap.md) | 5663 | 51 | Project documentation | Relative links PASS; context/status review |
| [docs/product/ui-design-system.md](../docs/product/ui-design-system.md) | 4543 | 57 | Project documentation | Relative links PASS; context/status review |
| [docs/product/ux-workflow.md](../docs/product/ux-workflow.md) | 13406 | 79 | Project documentation | Relative links PASS; context/status review |
| [docs/quality/test-strategy.md](../docs/quality/test-strategy.md) | 1823 | 25 | Project documentation | Relative links PASS; context/status review |
| [docs/security/admin-route-access-matrix.md](../docs/security/admin-route-access-matrix.md) | 4780 | 64 | Project documentation | Relative links PASS; context/status review |
| [docs/security/agent-collection-profile.md](../docs/security/agent-collection-profile.md) | 3821 | 37 | Project documentation | Relative links PASS; context/status review |
| [docs/security/security-baseline.md](../docs/security/security-baseline.md) | 3046 | 30 | Project documentation | Relative links PASS; context/status review |
| [docs/security/security-model.md](../docs/security/security-model.md) | 8098 | 79 | Project documentation | Relative links PASS; context/status review |
| [docs/technical-debt.md](../docs/technical-debt.md) | 3345 | 18 | Project documentation | Relative links PASS; context/status review |
| [docs/testing/testing-strategy.md](../docs/testing/testing-strategy.md) | 6346 | 95 | Project documentation | Relative links PASS; context/status review |
| [frontend/.gitkeep](../frontend/.gitkeep) | 0 | 0 | Browser UI | Reserved directory; no behavior |
| [frontend/app.js](../frontend/app.js) | 146786 | 981 | Browser UI | node syntax PASS; routes/API review; live hash comparison |
| [frontend/index.html](../frontend/index.html) | 54223 | 229 | Browser UI | IDs/controls structural check; no current browser acceptance |
| [frontend/src/features/.gitkeep](../frontend/src/features/.gitkeep) | 1 | 1 | Browser UI | Reserved directory; no behavior |
| [frontend/src/shared/.gitkeep](../frontend/src/shared/.gitkeep) | 1 | 1 | Browser UI | Reserved directory; no behavior |
| [frontend/styles.css](../frontend/styles.css) | 57220 | 251 | Browser UI | Inventory/role inspection |
| [infra/.gitkeep](../infra/.gitkeep) | 1 | 1 | Deployment/database | Reserved directory; no behavior |
| [infra/containers/.gitkeep](../infra/containers/.gitkeep) | 1 | 1 | Deployment/database | Reserved directory; no behavior |
| [infra/containers/Caddyfile](../infra/containers/Caddyfile) | 551 | 23 | Deployment/database | Configuration/source inspection; no current deployment/build |
| [infra/containers/docker-compose.free-demo.yml](../infra/containers/docker-compose.free-demo.yml) | 2737 | 68 | Deployment/database | Configuration/source inspection; no current deployment/build |
| [infra/containers/docker-compose.oracle-free.yml](../infra/containers/docker-compose.oracle-free.yml) | 547 | 17 | Deployment/database | Configuration/source inspection; no current deployment/build |
| [infra/containers/docker-compose.production.yml](../infra/containers/docker-compose.production.yml) | 2824 | 68 | Deployment/database | Configuration/source inspection; no current deployment/build |
| [infra/containers/docker-compose.yml](../infra/containers/docker-compose.yml) | 615 | 21 | Deployment/database | Configuration/source inspection; no current deployment/build |
| [infra/database/.gitkeep](../infra/database/.gitkeep) | 1 | 1 | Deployment/database | Reserved directory; no behavior |
| [infra/database/README.md](../infra/database/README.md) | 1607 | 31 | Deployment/database | Relative links PASS; context/status review |
| [infra/observability/.gitkeep](../infra/observability/.gitkeep) | 1 | 1 | Deployment/database | Reserved directory; no behavior |
| [installer/windows/AssetGuardAgent.iss](../installer/windows/AssetGuardAgent.iss) | 9204 | 194 | Installer source | Configuration/source inspection; no current deployment/build |
| [outputs/public-school-import/school-inventory-rk-demo.png](../outputs/public-school-import/school-inventory-rk-demo.png) | 60478 | binary | Public school demo artifact | Artifact inventory; no runtime/accuracy acceptance |
| [outputs/public-school-import/school-inventory-rk-demo.xlsx](../outputs/public-school-import/school-inventory-rk-demo.xlsx) | 5185 | binary | Public school demo artifact | Artifact inventory; no runtime/accuracy acceptance |
| [scripts/.gitkeep](../scripts/.gitkeep) | 1 | 1 | Repository configuration | Reserved directory; no behavior |
| [scripts/build_public_school_import.mjs](../scripts/build_public_school_import.mjs) | 3910 | 45 | Repository configuration | Inventory/role inspection |
| [scripts/linux/assetguard-backup-crypto.py](../scripts/linux/assetguard-backup-crypto.py) | 2422 | 54 | Linux production operations | AST PASS; selected behavior review |
| [scripts/linux/assetguard-server-backup.sh](../scripts/linux/assetguard-server-backup.sh) | 2481 | 55 | Linux production operations | Inventory/role inspection |
| [scripts/linux/assetguard-server-monitor.sh](../scripts/linux/assetguard-server-monitor.sh) | 5440 | 132 | Linux production operations | Inventory/role inspection |
| [scripts/linux/assetguard-server-restore-rehearsal.sh](../scripts/linux/assetguard-server-restore-rehearsal.sh) | 2175 | 25 | Linux production operations | Inventory/role inspection |
| [scripts/linux/install-server-backup.sh](../scripts/linux/install-server-backup.sh) | 2984 | 76 | Linux production operations | Inventory/role inspection |
| [scripts/linux/install-server-monitor.sh](../scripts/linux/install-server-monitor.sh) | 1835 | 57 | Linux production operations | Inventory/role inspection |
| [scripts/windows/README.md](../scripts/windows/README.md) | 21015 | 172 | Windows operations/Agent | Relative links PASS; context/status review |
| [scripts/windows/backup-crypto.ps1](../scripts/windows/backup-crypto.ps1) | 5027 | 106 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/backup-database.ps1](../scripts/windows/backup-database.ps1) | 3609 | 66 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/build-agent-installer.ps1](../scripts/windows/build-agent-installer.ps1) | 2303 | 52 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/collect-minimal-inventory.ps1](../scripts/windows/collect-minimal-inventory.ps1) | 2824 | 66 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/collect-phase0-inventory.ps1](../scripts/windows/collect-phase0-inventory.ps1) | 1597 | 44 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/glpi-agent-minimal-profile.cfg](../scripts/windows/glpi-agent-minimal-profile.cfg) | 455 | 5 | Windows operations/Agent | Configuration/source inspection; no current deployment/build |
| [scripts/windows/install-assetguard-agent-from-config.ps1](../scripts/windows/install-assetguard-agent-from-config.ps1) | 3799 | 97 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/install-assetguard-agent-service.ps1](../scripts/windows/install-assetguard-agent-service.ps1) | 11835 | 242 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/install-background-demo.ps1](../scripts/windows/install-background-demo.ps1) | 2192 | 27 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/install-backup-schedule.ps1](../scripts/windows/install-backup-schedule.ps1) | 2448 | 36 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/install-operations-telegram-monitor.ps1](../scripts/windows/install-operations-telegram-monitor.ps1) | 1391 | 17 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/install-pilot-agent-schedule.ps1](../scripts/windows/install-pilot-agent-schedule.ps1) | 1797 | 26 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/install-quick-tunnel-watchdog.ps1](../scripts/windows/install-quick-tunnel-watchdog.ps1) | 1336 | 20 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/invoke-latest-backup-rehearsal.ps1](../scripts/windows/invoke-latest-backup-rehearsal.ps1) | 3059 | 65 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/new-local-env.ps1](../scripts/windows/new-local-env.ps1) | 1303 | 28 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/prepare-pitch-incident.ps1](../scripts/windows/prepare-pitch-incident.ps1) | 5686 | 102 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/request-assetguard-agent-reenrolment.ps1](../scripts/windows/request-assetguard-agent-reenrolment.ps1) | 3144 | 81 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/restore-database.ps1](../scripts/windows/restore-database.ps1) | 1692 | 29 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/run-quick-tunnel-watchdog.ps1](../scripts/windows/run-quick-tunnel-watchdog.ps1) | 2143 | 46 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/run-scheduled-inventory.ps1](../scripts/windows/run-scheduled-inventory.ps1) | 922 | 17 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/send-minimal-inventory.ps1](../scripts/windows/send-minimal-inventory.ps1) | 2767 | 64 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/send-operations-telegram-alert.ps1](../scripts/windows/send-operations-telegram-alert.ps1) | 4572 | 75 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/set-backup-passphrase.ps1](../scripts/windows/set-backup-passphrase.ps1) | 1620 | 34 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/set-telegram-credentials.ps1](../scripts/windows/set-telegram-credentials.ps1) | 1184 | 26 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/start-demo.ps1](../scripts/windows/start-demo.ps1) | 2290 | 37 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/start-free-public-demo.ps1](../scripts/windows/start-free-public-demo.ps1) | 1395 | 32 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/start-local-quick-tunnel.ps1](../scripts/windows/start-local-quick-tunnel.ps1) | 1779 | 31 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/start-local-vision-demo.ps1](../scripts/windows/start-local-vision-demo.ps1) | 2573 | 57 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/test-assetguard-agent-readiness.ps1](../scripts/windows/test-assetguard-agent-readiness.ps1) | 5771 | 104 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/test-local-vision-demo.ps1](../scripts/windows/test-local-vision-demo.ps1) | 5097 | 92 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/uninstall-assetguard-agent-service.ps1](../scripts/windows/uninstall-assetguard-agent-service.ps1) | 3404 | 63 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/uninstall-background-demo.ps1](../scripts/windows/uninstall-background-demo.ps1) | 424 | 8 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/uninstall-quick-tunnel-watchdog.ps1](../scripts/windows/uninstall-quick-tunnel-watchdog.ps1) | 274 | 6 | Windows operations/Agent | PowerShell parser PASS; selected flow review |
| [scripts/windows/verify-backup-restore.ps1](../scripts/windows/verify-backup-restore.ps1) | 6301 | 123 | Windows operations/Agent | PowerShell parser PASS; selected flow review |

## Локальные файлы вне Git

- `.env` и runtime credentials не выводились; содержимое секретов не включено в отчёт.
- `installer-output/`: локальные версии installer; для 0.1.6/0.1.7 проверены Authenticode и SHA-256, повторная сборка/установка не выполнялась.
- `outputs/AssetGuard_инструкция_для_продолжения_разработки.docx`: извлечён текст и сопоставлен с актуальным checklist; обнаружен устаревший handoff.
- `tmp/`, `acl-probe.txt`, `.local/`, caches/venv/dependencies сохранены; не удалялись и не добавлялись автоматически в Git.
- Модели, пользовательские raw inventories/backup SQL и другие чувствительные runtime данные не выгружались для этого аудита.
- Два новых Markdown-отчёта созданы как результат текущего аудита; исходные файлы проекта не изменены.
