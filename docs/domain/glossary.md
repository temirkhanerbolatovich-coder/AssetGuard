# Словарь предметной области

| Термин | Значение |
| --- | --- |
| Organization | Владелец учёта; в MVP одна организация |
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

## Инварианты

1. Один ManagedEndpoint имеет не более одного `ACTIVE` baseline.
2. RawInventory никогда не меняется после сохранения.
3. Новый snapshot — candidate, пока администратор явно не примет его как baseline.
4. PARTIAL/UNKNOWN inventory не создаёт removal по отсутствующей категории.
5. Каждый ChangeEvent содержит evidence и deterministic deduplication key.
6. Hostname — наблюдаемый атрибут, но не единственная identity.
7. Решения и history append-only.
8. Baseline меняется только через явное `accept_snapshot_as_baseline`; normalizer никогда не делает этого сам.
9. Diff RAM/STORAGE разрешён только когда соответствующая категория current snapshot имеет `COMPLETE`.
