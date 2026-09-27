# Реализованные возможности

Раздел служит картой подтверждённых функций и не дублирует их подробные контракты.

| Возможность | Где подтверждена |
| --- | --- |
| GLPI XML transport и JSON bridge | [API](../api/README.md), [integration](../integration/glpi-agent-transport-decision.md) |
| Raw evidence, snapshots, baseline, changes и incidents | [Data flow](../architecture/data-flow.md), [ADR-002](../decisions/ADR-002-baseline-and-evidence.md) |
| Иерархия локаций, активы и физические проверки | [Inventory operating model](../product/inventory-operating-model.md), integration tests |
| Named users, sessions, roles, tenant и room scope | [Security model](../security/security-model.md) |
| Dashboard, поиск, карточка оборудования и история | [UX workflow](../product/ux-workflow.md), browser E2E tests |
| PDF/OCR import, QR и PDF-акты | [PDF/OCR](../operations/pdf-import-ocr.md), unit tests |
| AssetGuard Vision | [Vision requirements](../product/assetguard-vision-requirements.md), [data flow](../architecture/data-flow.md) |

Текущий статус и незавершённые продуктовые задачи ведутся в [project checklist](../product/current-project-checklist.md); технические ограничения — в [technical debt](../technical-debt.md).
