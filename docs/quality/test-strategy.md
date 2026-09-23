# Стратегия проверки MVP

## Слои

| Слой | Проверяемое свойство |
| --- | --- |
| Unit | canonicalization, placeholders, identity confidence, matching, diff, dedup keys |
| Integration | raw → snapshot → baseline → event → incident → history в PostgreSQL |
| Contract | наблюдаемый GLPI Agent ingest контракт после spike |
| End-to-end | обязательный demo-сценарий через API/UI |

## Обязательные sanitized fixtures

1. RAM A + RAM B + SSD X.
2. Та же машина: RAM A + SSD X — removal RAM B.
3. RAM A + B + SSD X, затем SSD Y — removed X и added Y; replacement лишь при достаточных evidence.
4. Идентичный scan — ноль новых ChangeEvent.
5. PARTIAL SOFTWARE inventory — ноль hardware removal events.
6. Hostname change — `HOSTNAME_CHANGED`, без нового Asset.

Фикстуры хранятся без secrets и персональных данных в `backend/tests/fixtures/`.

Статус на 2026-09-23: все шесть сценариев представлены отдельными sanitized JSON fixtures. Для минимального privacy-профиля добавлен unit-check: запрещённые top-level категории не должны попасть в `content`. Следующий тестовый шаг — изолировать PostgreSQL fixture database и автоматизировать полную цепочку для каждого сценария без использования локальной demo-базы.
