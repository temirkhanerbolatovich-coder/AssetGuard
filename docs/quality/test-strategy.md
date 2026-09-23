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

Статус на 2026-09-23: 13 pytest tests проходят на disposable PostgreSQL database. Проверяются все шесть fixture-сценариев, полная inventory цепочка, RBAC, revoke/logout/disable user, authenticated audit actor, version-tolerant envelope schema, endpoint identity change/conflict и Vision workflow. GitHub Actions поднимает PostgreSQL, запускает tests, `pip check`, JavaScript syntax check и production Compose validation. Vision integration test использует детерминированный detector; реальный Grounding DINO остаётся отдельным ручным smoke-сценарием. Следующий уровень — browser E2E и optional real-model CI job.
