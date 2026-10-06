# Словарь предметной области

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

| Термин | Значение |
| --- | --- |
| Organization | Tenant-владелец учёта: школа или другая отдельная организация |
| Asset | Учётный физический объект с inventory number |
| ManagedEndpoint | Техническая identity устройства, которое сообщает инвентаризацию |
| EndpointIdentifier | Наблюдаемый идентификатор endpoint с confidence и временем актуальности |
| RawInventory | Неизменяемый исходный payload от источника |
| HardwareSnapshot | Нормализованное наблюдение оборудования, производное от RawInventory |
| ComponentObservation | Факт наблюдения детали в snapshot |
| ComponentIdentity | Гипотеза о том, что несколько observations относятся к одной физической детали |
| Baseline | Явно подтверждённое состояние для сравнения |
| ChangeEvent | Объяснимый технический факт различия baseline и current snapshot |
| Incident | Workflow над ChangeEvent, а не замена факта |
| IncidentDecision | Append-only административное решение по Incident |
| AssetHistoryEntry | Append-only элемент общей временной шкалы |
| AgentCredential | Отдельный username и hash секрета, разрешающий одному Agent отправлять inventory |
| AgentReenrolment | Короткоживущий запрос на перевыпуск AgentCredential после переустановки Windows |
| TelegramNotification | Tenant-bound запись outbox; SENT означает принятие Telegram, а RETRYING вычисляется для PENDING с attempts > 0 |
| Agent delivery queue | Защищённая bounded FIFO локальных XML; хранит неотправленные hardware reports до ACK |
| STALE | Отсутствие свежего inventory по threshold; вычисляемая категория, а не доказательство пропажи |
| Room QR | Авторизованная ссылка `#room-audit=UUID` для запуска полного обхода |
| LocationGrant | Право `VIEWER` или `EDITOR` на корпус, этаж либо кабинет |

## Инварианты

1. Один ManagedEndpoint имеет не более одного `ACTIVE` baseline.
2. Evidence fields RawInventory (payload/hash/source/time/type) неизменяемы; processing metadata может изменяться, удаление записи запрещено.
3. Новый snapshot — candidate, пока администратор явно не примет его как baseline.
4. PARTIAL/UNKNOWN inventory не создаёт removal по отсутствующей категории.
5. Каждый ChangeEvent содержит evidence и deterministic deduplication key.
6. Hostname — наблюдаемый атрибут, но не единственная identity.
7. Решения и history append-only.
8. Baseline меняется только через явное `accept_snapshot_as_baseline`; normalizer никогда не делает этого сам.
9. Diff RAM/STORAGE разрешён только когда соответствующая категория current snapshot имеет `COMPLETE`.
10. У ManagedEndpoint одновременно может быть не более одного активного AgentCredential; re-enrolment отзывает предыдущий активный credential.
11. Hardware identifier используется для сопоставления endpoint, но не является секретом или самостоятельной аутентификацией.
