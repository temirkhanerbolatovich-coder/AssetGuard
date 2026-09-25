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
| [product](product/) | Demo-сценарий, [актуальный полный чек-лист](product/current-project-checklist.md), [архитектура и pitch-гайд](product/pitch-guide.md), границы MVP, [чек-лист завершения](product/mvp-completion-checklist.md), [аудит данных Dashboard](product/dashboard-data-audit.md), [план frontend redesign](product/frontend-redesign-audit.md) и [UX-сценарии пользователей](product/ux-workflow.md) |
| [quality](quality/) | Фикстуры и стратегия проверки |
| [operations](operations/) | Среда, наблюдаемость, [PDF/OCR импорт](operations/pdf-import-ocr.md), backup и журналирование |

## Установка Agent на другие компьютеры

Для нескольких Windows-компьютеров используйте мастер `AssetGuard-Agent-Setup-0.1.5.exe`, а не копирование рабочей папки проекта. Он запрашивает уникальные учётные данные устройства, устанавливает GLPI Agent как службу с автозапуском и включает только аппаратный профиль сбора. Сборка EXE, ограничения и проверка первого подключения описаны в [Windows operations](../scripts/windows/README.md#графический-установщик-для-других-компьютеров).

Текущее состояние всего продукта, незакрытые функции и порядок дальнейшей разработки собраны в [актуальном полном чек-листе](product/current-project-checklist.md).

Наблюдения реального GLPI Agent и результаты executable tests имеют приоритет над предположениями в документации. Незавершённые production и Vision-camera возможности явно перечисляются в соответствующих разделах.
