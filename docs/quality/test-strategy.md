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

Статус на 2026-09-23: pytest tests проходят на disposable PostgreSQL database. Проверяются fixture-сценарии, JSON bridge и native GLPI XML PROLOG/INVENTORY, полная inventory цепочка, RBAC, endpoint identity и Vision workflow. GitHub Actions поднимает PostgreSQL, запускает tests, `pip check`, JavaScript/PowerShell syntax checks и production Compose validation. Отдельный ручной и еженедельный job `Grounding DINO real-model smoke` устанавливает `backend[vision]`, кэширует Hugging Face model и обрабатывает demo-кадр настоящей моделью. Это runtime smoke, а не тест точности распознавания.
