# Развёртывание

## Поддерживаемые конфигурации

| Режим | Конфигурация | Назначение |
| --- | --- | --- |
| Локальная разработка | `infra/containers/docker-compose.yml` | PostgreSQL на loopback, backend запускается отдельно |
| Локальная демонстрация | `docker-compose.free-demo.yml` | Временный Cloudflare Quick Tunnel без собственного домена |
| Production | `docker-compose.production.yml` + Caddy | HTTPS, private Docker network, persistent PostgreSQL/Vision volumes |
| Oracle Free | `docker-compose.oracle-free.yml` overlay | Ограниченный серверный профиль без Vision dependencies |

Проверенные пошаговые инструкции находятся в [local demo guide](../operations/local-demo-guide.md), [free deployment](../operations/free-deployment.md) и [production deployment](../operations/production-deployment.md).

## Runtime topology

Production публикует только Caddy на портах 80/443. Caddy передаёт запросы FastAPI; API подключается к PostgreSQL по internal network. При старте image применяет Alembic migrations перед Uvicorn. PostgreSQL, Vision images, Hugging Face cache и Caddy state находятся в named volumes.

## Эксплуатация

- Windows automation и agent installer: `scripts/windows/README.md`.
- Linux server backup, restore rehearsal и monitoring: `scripts/linux/`.
- Наблюдаемость: [observability.md](../operations/observability.md).
- Backup и recovery: разделы production runbook.

Перед production deployment обязательны уникальные secrets, DNS, открытые 80/443, persistent volumes и проверка `/health` и `/health/ready`. End-to-end цикл encrypted upload → download → isolated restore из Cloudflare R2 подтверждён 2026-09-27 через Windows Task Scheduler и постоянный Linux server. Server backup, restore rehearsal и monitor timers установлены; Telegram test alert принят, повторный запуск подавлен дедупликацией.

Application commit `93ff8ed` развёрнут 2026-10-04 на schema `0025_agent_reenrolment`; public UI hashes, readiness и защищённые re-enrolment routes проверены. Свежая pre-deployment R2-копия на `0024` прошла isolated restore и upgrade/downgrade/re-upgrade с проверкой всех существующих таблиц и запуском старого/нового API. Старый API image сохранён, но его обычный startup не понимает revision `0025`: откат требует отдельного решения по новым данным re-enrolment. Точный протокол и актуальный backup/restore — в [production runbook](../operations/production-deployment.md) и [release acceptance](../../outputs/assetguard-release-2026-10-04.md).
