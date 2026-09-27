# Документация AssetGuard

Каноническое техническое описание строится от текущего кода, migrations, tests и deployment configuration. Сохранённые исходные требования находятся в `ASSETGUARD_MVP_v0.1_REQUIREMENTS.md`, но при расхождении фактическое поведение определяется кодом и executable tests.

## Начать отсюда

- [Обзор архитектуры](architecture/overview.md)
- [Потоки данных](architecture/data-flow.md)
- [Реализованные возможности](features/README.md)
- [Архитектурные решения](decisions/README.md)
- [Модель безопасности](security/security-model.md)
- [Стратегия тестирования](testing/testing-strategy.md)
- [Развёртывание](deployment/README.md)
- [Технический долг](technical-debt.md)

## Дополнительные материалы

| Раздел | Назначение |
| --- | --- |
| [api](api/) | Реализованные HTTP boundaries |
| [domain](domain/) | Словарь сущностей и правила состояния |
| [integration](integration/) | GLPI Agent transport, privacy profile и результаты spike |
| [operations](operations/) | Локальная среда, production runbooks, наблюдаемость, backup и PDF/OCR |
| [product](product/) | Требования, UX, demo и [текущий checklist](product/current-project-checklist.md) |
| [quality](quality/) | Историческая стратегия качества и fixtures; актуальная стратегия находится в [testing](testing/testing-strategy.md) |

Для установки GLPI Agent на другие Windows-компьютеры используйте инструкции в [Windows operations](../scripts/windows/README.md#графический-установщик-для-других-компьютеров). Известные расхождения старых документов с реализацией зафиксированы в [technical debt](technical-debt.md), а не скрыты обновлённым индексом.
