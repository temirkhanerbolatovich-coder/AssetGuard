# Документация AssetGuard

Документы ниже являются рабочей базой проекта. Исходным источником требований остаётся `ASSETGUARD_MVP_v0.1_REQUIREMENTS.md` в корне репозитория.

| Раздел | Назначение |
| --- | --- |
| [architecture](architecture/) | Границы modular monolith, фактическая структура и Vision integration |
| [domain](domain/) | Словарь сущностей и правила состояния |
| [decisions](decisions/) | Архитектурные решения (ADR) |
| [integration](integration/) | Контракт и план проверки GLPI Agent |
| [api](api/) | Реализованные REST API boundaries |
| [data](data/) | Владение данными, хранение и retention |
| [security](security/) | Минимальная модель безопасности и privacy |
| [product](product/) | Demo-сценарий, границы MVP, [чек-лист завершения](product/mvp-completion-checklist.md) и [аудит данных Dashboard](product/dashboard-data-audit.md) |
| [quality](quality/) | Фикстуры и стратегия проверки |
| [operations](operations/) | Среда, наблюдаемость и журналирование |

Наблюдения реального GLPI Agent и результаты executable tests имеют приоритет над предположениями в документации. Незавершённые production и Vision-camera возможности явно перечисляются в соответствующих разделах.
