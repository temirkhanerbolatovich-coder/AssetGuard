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

Перед production deployment обязательны уникальные secrets, DNS, открытые 80/443, persistent volumes и проверка `/health` и `/health/ready`. После deployment требуется реальный restore rehearsal; текущая проблема R2 зафиксирована как [TD-001](../technical-debt.md).
