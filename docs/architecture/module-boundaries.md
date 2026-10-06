# Границы модулей

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

| Модуль | Владеет | Не должен делать |
| --- | --- | --- |
| Inventory | Приём payload, проверка размера/схемы, RawInventory, source adapters | Менять baseline или интерпретировать отсутствие компонента как removal |
| Snapshots | Нормализация и completeness наблюдений | Удалять raw payload |
| Identity | Пользователи, сессии, роли, Agent credentials, re-enrolment и location grants | Хранить plaintext password/claim token или обходить tenant scope |
| Endpoint matching | Canonical hardware identifiers, placeholder denylist, confidence и сопоставление | Считать hostname единственной identity или использовать UUID как секрет |
| Baselines | Candidate/accept/supersede/reject | Автоматически принимать новый snapshot |
| Changes | Сравнение baseline/current, evidence, dedup key | Ставить диагноз theft или создавать workflow без факта |
| Incidents | Incident status и append-only decisions | Переписывать технический ChangeEvent |
| History | Unified append-only timeline | Быть единственным источником состояния бизнес-сущностей |
| Assets/Endpoints | Учёт объекта и технической identity, связь между ними | Сливать Asset и ManagedEndpoint в одну сущность |
| Notifications | Transactional event outbox, tenant routing, retry и delivery metadata | Отправлять HTTP в транзакции создания incident или показывать secrets/payload в UI |
| Vision | Scans, images, detections, room baseline и comparison | Подтверждать кражу или изменять hardware baseline |

Допустимый поток зависимостей: interfaces/infrastructure → application modules → domain rules. В текущем монолите HTTP/application workflows используют сервисы и SQLAlchemy models нескольких модулей в общей транзакции. Это организационные границы ответственности, а не строгая изоляция persistence. Новые изменения должны сохранять правила evidence, scope и атомарности; выделять отдельные repository/service layers без конкретной потребности не требуется.
