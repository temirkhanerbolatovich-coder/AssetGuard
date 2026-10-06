# GLPI Agent: version lock

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

## Выбранный артефакт для лабораторного стенда

При отображении карточки версии `1.19`/`1.20` и XML-представления `GLPI-Agent_v1.19`/`GLPI-Agent_v1.20` считаются одним проверенным релизом. Исходное `source_version` в raw evidence и API сохраняется буквально; нормализация применяется только к проверке поддержки. Неизвестные версии, произвольные префиксы, patch-версии и дополнительные суффиксы остаются `UNSUPPORTED`, отсутствие версии — `UNKNOWN`. Это не расширяет список поддержанных релизов и не разрешает автоматическое принятие эталона. [Локальная проверка 2026-10-06](../../outputs/assetguard-agent-status-fixes-2026-10-06/report.md).

| Параметр | Значение |
| --- | --- |
| Проект | GLPI Agent (`glpi-project/glpi-agent`) |
| Версия новых установок | 1.20 |
| Поддерживаемая предыдущая версия | 1.19 |
| Платформа | Windows x64 |
| WinGet package | `GLPI-Project.GLPI-Agent` |
| Официальный источник | WinGet manifest и GitHub Releases проекта GLPI Agent |
| Лицензия upstream | GPL-2.0-or-later |

## Назначение

Графический AssetGuard installer закрепляет новые установки на GLPI Agent 1.20 и явно указывает WinGet source. Существующая версия 1.19 остаётся совместимой, чтобы обновление установленных pilot-PC не было обязательным. Любая следующая версия требует отдельной проверки release notes, цифровой подписи, transport contract и регрессии canonicalization/diff на сохранённых sanitized fixtures.

## Безопасная последовательность внедрения

1. Получить upstream MSI/portable package исключительно из официального release.
2. Сверить SHA-256 с опубликованной суммой.
3. Установить без `NO_SSL_CHECK`, без production secrets и без фоновой отправки на непроверенный endpoint.
4. Снять локальный full inventory и санитаризировать его.
5. Проверить payload, complete/partial semantics, identity fields и retry.
6. Только затем настраивать Inventory Gateway или выбирать GLPI 11 sidecar.

## Текущее состояние

На 23.09.2026 GLPI Agent 1.19 прошёл локальный payload и native transport spike. На 27.09.2026 неизменённый GLPI Agent 1.20, установленный WinGet на втором реальном Windows-PC, успешно выполнил authenticated native отправку в production: RawInventory получил `PROCESSED`, endpoint — `ONLINE`. Integration contract теперь прогоняется для метаданных версий 1.19 и 1.20. 5 октября installer 0.1.8 с неизменённым collector 1.19 дополнительно прошёл continuous collection и controlled offline/lost-ACK delivery. Новые установки остаются pinned на 1.20; на 6 октября 0.1.8 не подписан и не опубликован как новый release. [Протокол и границы](../../outputs/assetguard-agent-reliability-2026-10-05.md). Это подтверждает используемый AssetGuard XML boundary, но не объявляет совместимость с будущими версиями.
