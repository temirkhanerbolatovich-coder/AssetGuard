# Границы модулей

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
| Vision | Scans, images, detections, room baseline и comparison | Подтверждать кражу или изменять hardware baseline |

Допустимый поток зависимостей: interfaces/infrastructure → application modules → domain rules. Модули взаимодействуют через явные контракты/команды, а не через прямое чтение внутренних таблиц друг друга.
