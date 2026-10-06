# Реализованные возможности

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Раздел служит картой подтверждённых функций и не дублирует их подробные контракты.

| Возможность | Где подтверждена |
| --- | --- |
| GLPI XML transport и JSON bridge | [API](../api/README.md), [integration](../integration/glpi-agent-transport-decision.md) |
| Raw evidence, snapshots, baseline, changes и incidents | [Data flow](../architecture/data-flow.md), [ADR-002](../decisions/ADR-002-baseline-and-evidence.md) |
| Иерархия локаций, активы и физические проверки | [Inventory operating model](../product/inventory-operating-model.md), integration tests |
| Named users, sessions, roles, tenant и room scope | [Security model](../security/security-model.md) |
| Per-Agent credentials, revoke и подтверждаемое re-enrolment | [Agent ADR](../decisions/ADR-005-agent-reenrolment.md), [Windows operations](../../scripts/windows/README.md) |
| Dashboard, поиск, карточка оборудования и история | [UX workflow](../product/ux-workflow.md), browser E2E tests |
| Реестр, карточки и единый центр инцидентов | [Этап UI/UX 2](registry-and-incident-center.md), browser E2E и tenant/location tests |
| Кабинеты, обход с итогом и импорт | [Этап UI/UX 3](rooms-inspection-and-import.md), атомарные ошибки Excel/PDF и browser E2E |
| Экран входа, каркас и состояния запросов | [Этап UI/UX 1](frontend-shell-and-auth.md), [ТЗ](../product/ui-ux-modernization-spec.md) |
| PDF/OCR import, QR и PDF-акты | [PDF/OCR](../operations/pdf-import-ocr.md), unit tests |
| Agent 0.1.8: continuous collection и durable delivery | [Контракт](agent-continuous-inventory.md), [ADR-008](../decisions/ADR-008-agent-durable-delivery.md), runtime/native tests |
| Agent, сотрудники и delivery metadata | [Администрирование](agent-administration-and-delivery.md), authorization и browser tests |
| Ledger UI и упрощённые рабочие сценарии | [Полный редизайн](ui-ledger-redesign.md), [UI acceptance](../testing/ui-acceptance.md), 21 browser E2E |
| QR кабинета, scan имущества и session draft | [Обход и импорт](rooms-inspection-and-import.md), route matrix и browser E2E |
| AssetGuard Vision | [Vision requirements](../product/assetguard-vision-requirements.md), [data flow](../architecture/data-flow.md) |
| Encrypted R2 backup, restore rehearsal и Telegram monitoring | [Production runbook](../operations/production-deployment.md), [observability](../operations/observability.md) |
| Уведомления о новых технических/физических инцидентах | [Telegram queue](telegram-notifications.md), [ADR-007](../decisions/ADR-007-telegram-outbox.md) |

Текущий статус и незавершённые продуктовые задачи ведутся в [project checklist](../product/current-project-checklist.md); технические ограничения — в [technical debt](../technical-debt.md). Installer `0.1.8`, managed update/rollback и fleet validation разделяются намеренно: наличие кода re-enrolment не означает завершённую приёмку на реальных ПК.
