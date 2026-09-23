# GLPI Agent: version lock для Phase 0

## Выбранный артефакт для лабораторного стенда

| Параметр | Значение |
| --- | --- |
| Проект | GLPI Agent (`glpi-project/glpi-agent`) |
| Версия | 1.19 |
| Платформа | Windows x64 |
| Артефакт | `GLPI-Agent-1.19-x64.msi` |
| Официальный источник | GitHub Releases проекта GLPI Agent |
| SHA-256, опубликованный проектом | `f3f933a54bc325ffe0d6063e177874e05138dd887fe690adef337640e8d6335c` |
| Лицензия upstream | GPL-2.0-or-later |

## Назначение

Версия закреплена только для воспроизводимого Phase 0 на текущем Windows x64 стенде. Обновление агента требует отдельной проверки release notes, цифровой подписи, SHA-256 и регрессии canonicalization/diff на сохранённых sanitized fixtures.

## Безопасная последовательность внедрения

1. Получить upstream MSI/portable package исключительно из официального release.
2. Сверить SHA-256 с опубликованной суммой.
3. Установить без `NO_SSL_CHECK`, без production secrets и без фоновой отправки на непроверенный endpoint.
4. Снять локальный full inventory и санитаризировать его.
5. Проверить payload, complete/partial semantics, identity fields и retry.
6. Только затем настраивать Inventory Gateway или выбирать GLPI 11 sidecar.

## Текущее состояние

На 23.09.2026 GLPI Agent 1.19 установлен через официальный WinGet package `GLPI-Project.GLPI-Agent` и проверен командой `--version`. Локальный full inventory получен штатной утилитой `glpi-inventory --json`; server URL, credentials и внешняя передача данных не использовались. Результат Phase 0 зафиксирован в [наблюдении реального payload](phase0-local-inventory-observation.md).
