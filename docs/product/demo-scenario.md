# Демонстрационный сценарий MVP

1. PC-001 сообщает RAM A123, RAM B456 и SSD S991.
2. Система сохраняет immutable RawInventory и создаёт Snapshot #1.
3. Администратор связывает endpoint с Asset и явно принимает Snapshot #1 как baseline.
4. Следующий полный scan содержит RAM A123 и SSD S991, но не B456.
5. Система создаёт объяснимый `COMPONENT_REMOVED` для RAM B456 и ровно один Incident.
6. Администратор классифицирует Incident; решение видно в history.
7. Если изменение подтверждено, администратор отдельным действием принимает current snapshot как новый baseline.
8. Идентичный повторный scan не создаёт новых ChangeEvent/Incident.

## Недопустимые трактовки

- PARTIAL software inventory не должен означать удаление RAM/SSD.
- Изменение не должно автоматически называться кражей.
- Закрытие Incident не должно само по себе менять baseline.

