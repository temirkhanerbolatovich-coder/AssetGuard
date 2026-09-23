# Стратегия проверки MVP

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

Статус на 2026-09-23: все шесть сценариев представлены sanitized JSON fixtures. Pytest поднимает изолированную PostgreSQL test database и проверяет полную inventory цепочку, RBAC и Vision workflow. Vision integration test использует детерминированный detector, чтобы не скачивать ML weights в обычном test run; реальный Grounding DINO проверяется отдельным ручным smoke-сценарием на demo-паре изображений. Следующий уровень проверки — browser E2E и optional model smoke job.
