# Архитектурные решения

ADR фиксируют решения, которые влияют на архитектуру, безопасность, эксплуатацию или долгосрочную стоимость изменений. Они объясняют контекст и компромиссы, но не заменяют документацию текущего поведения.

## Реестр

| ADR | Решение | Статус в документе |
| --- | --- | --- |
| [ADR-001](ADR-001-modular-monolith.md) | Модульный монолит | Accepted |
| [ADR-002](ADR-002-baseline-and-evidence.md) | Baseline и сохранение свидетельств | Accepted |
| [ADR-003](ADR-003-glpi-source-boundary.md) | GLPI Agent как внешняя граница сбора | Accepted |
| [ADR-004](ADR-004-backend-stack.md) | FastAPI, SQLAlchemy, Alembic и PostgreSQL | Accepted |
| [ADR-005](ADR-005-agent-reenrolment.md) | Подтверждаемое восстановление Agent по SMBIOS UUID | Accepted |
| [ADR-006](ADR-006-import-accounting-precedence.md) | Учётные акты имеют приоритет над повторным импортом | Accepted |
| [ADR-007](ADR-007-telegram-outbox.md) | Транзакционная очередь Telegram и bounded worker | Accepted |
| [ADR-008](ADR-008-agent-durable-delivery.md) | Локальный сбор и ограниченная очередь Windows Agent | Accepted |

## Когда нужен ADR

Создавайте ADR, если решение меняет один из следующих аспектов:

- границы модулей или deployment topology;
- authentication, authorization или модель доверия;
- основное хранилище, протокол интеграции или жизненный цикл данных;
- стратегию очередей, retry, backup или recovery;
- значимый dependency либо осознанный security trade-off.

Локальные реализации и обратимые детали не требуют ADR. Для нового решения скопируйте [ADR-TEMPLATE.md](ADR-TEMPLATE.md), присвойте следующий номер и добавьте запись в таблицу. Принятое решение не переписывают задним числом: изменение оформляют новым ADR, который помечает прежний как `Superseded`.

Допустимые статусы: `Proposed`, `Accepted`, `Rejected`, `Deprecated`, `Superseded by ADR-XXX`.
