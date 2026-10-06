# Наблюдаемость и аудит

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

## Текущий контур

Сверка 2026-10-06: schema `0026`, application `f4f56e7`. Server monitor выполняется раз в 5 минут, Telegram incident worker — раз в минуту. Monitor, notifications, backup и restore-rehearsal timers активны; последние jobs — success/0. [Аудит и dated snapshot](../quality/project-audit-2026-10-06.md).

`/health` подтверждает доступность процесса. `/health/ready` выполняет SQL `SELECT 1` и возвращает 503 при недоступной БД. Эти ответы не идентифицируют deployed Git SHA, актуальность всех инцидентов или готовность fleet. Защищённый `/admin/operations/status` возвращает scoped Agent/ingest/notification aggregates и database/storage metadata.

## Agent freshness

`agents.stale` вычисляется при чтении по `last_seen_at` и `ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS` (24 часа по умолчанию). Старые ONLINE/REQUIRES_VERIFICATION учитываются как stale; OFFLINE/IDENTITY_CONFLICT отдельно. Tenant/location filters применяются до агрегации; чтение не запускает maintenance и не изменяет endpoint. Отсутствие данных не доказывает пропажу/кражу.

Read-only срез 6 октября **17:29:16 UTC+5**: 11 endpoints, **6 online / 5 stale**, 0 identity conflicts и failed ingests. Пять stale PC требуют проверки по месту. Inventory/snapshot counts растут; числа среза не объявляются постоянными.

Agent 0.1.8 ведёт protected `runtime.jsonl`, pending/rejected и delivery deadlines. `COLLECTED` отличается от `DELIVERED`; очередь сохраняет данные при network/auth/quota errors. [Диагностика и границы](../features/agent-continuous-inventory.md). Server snapshot timestamp пока receipt time, даже для offline captures.

## Telegram и monitor

Новые technical/physical incidents создают outbox в одной транзакции с evidence. Minute worker выбирает только явно настроенный tenant, проверяет acceptance/chat/message id и сохраняет SENT. `/admin/notifications` доступен ADMIN и отдаёт metadata без recipient/payload/token. SENT не подтверждает прочтение. [Контракт](../features/telegram-notifications.md), [панель](../features/agent-administration-and-delivery.md).

Monitor проверяет readiness, Compose, disk, backup age/job failures, Agent freshness, failed ingest/conflicts, notification job и retry aggregates. State default — `/var/lib/assetguard-monitor`; `--state-dir` позволяет отделить controlled checks.

Одинаковые проблемы подавляются на 4 часа только после Telegram `ok=true` с message_id. Здоровый run очищает fingerprint; возвращение проблемы вызывает новый alert. Отказ доставки сохраняет возможность retry. Aggregated fingerprint не описывает индивидуальные переходы Agent; отдельного recovery message пока нет.

На read-only срезе 6 октября: 3 SENT, ожидающих сообщений нет. Новое тестовое сообщение в этом аудите не отправлялось. Реальное acceptance и подтверждение пользователя сохранены в [протоколе Telegram 5 октября](../../outputs/assetguard-telegram-2026-10-05.md); повтор/отказ/recovery проверены автоматическими tests. Настоящий API outage/failover drill остаётся staging-задачей.

## Логи и recovery

Application фиксирует request/status/duration, received/rejected inventory, normalization/conflicts, snapshots/changes/incidents, baseline и решения. Domain history append-only, но отдельный полный журнал users/grants/credentials/settings и audit UI ещё нужны. Caddy удаляет admin token, Authorization и Cookie из access logs. Не сохраняйте hardware XML, passwords/tokens и фотографии в публичный report.

Текущая последняя R2-копия: `assetguard-production-20261006-075950.sql.agbackup`. Status и journal подтверждают upload/isolated restore на `0026`, 220 assets/11 endpoints; backup/restore services success. Копия PostgreSQL не восстанавливает Vision image volume. Новый restore в этом аудите не запускался.

[Production runbook](production-deployment.md), [PDF/OCR](pdf-import-ocr.md), [локальный demo](local-demo-guide.md), [fleet](agent-fleet-pilot.md), [technical debt](../technical-debt.md). Исторические результаты `0024`/`0025` находятся в датированных release records.
