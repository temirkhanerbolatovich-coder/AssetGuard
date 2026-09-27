# Стратегия проверки MVP

> **Исторический документ.** Это ранняя стратегия demo MVP. Текущий набор, команды запуска, CI и эксплуатационные проверки описаны в [актуальной стратегии тестирования](../testing/testing-strategy.md).

## Слои

| Слой | Проверяемое свойство |
| --- | --- |
| Unit | canonicalization, placeholders, identity confidence, matching, diff, dedup keys |
| Integration | raw → snapshot → baseline → event → incident → history в PostgreSQL |
| Contract | наблюдаемый GLPI Agent ingest контракт после spike |
| End-to-end | обязательные inventory и Vision demo-сценарии через API |

## Обязательные sanitized fixtures

1. RAM A + RAM B + SSD X.
2. Та же машина: RAM A + SSD X — removal RAM B.
3. RAM A + B + SSD X, затем SSD Y — removed X и added Y; replacement лишь при достаточных evidence.
4. Идентичный scan — ноль новых ChangeEvent.
5. PARTIAL SOFTWARE inventory — ноль hardware removal events.
6. Hostname change — `HOSTNAME_CHANGED`, без нового Asset.

Фикстуры хранятся без secrets и персональных данных в `backend/tests/fixtures/`.

Статус на 2026-09-23 сохранён как историческое свидетельство: pytest проходил на disposable PostgreSQL database, а GitHub Actions проверял backend, JavaScript/PowerShell и Compose. Документ не отражает более поздние Agent lifecycle, tenant matrix, backup и browser E2E проверки.
