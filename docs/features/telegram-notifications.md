# Telegram: инциденты и эксплуатационные проблемы

Дата: 2026-10-05. Область: новые технические и физические инциденты, проблемы Agent и сервера.

## Что отправляется

- Новый технический инцидент после сравнения snapshot с подтверждённым baseline: объект, компонент, вид изменения, приоритет, время и ссылка на карточку с подробным сравнением было/стало.
- Новый физический инцидент при обходе: имущество, кабинет, результат проверки, количество и ссылка на кабинет.
- Сводные проблемы сервера/Agent: readiness, остановленные Compose services, диск, backup/restore, отсутствие свежей телеметрии, ingest, identity conflicts, failed notification job и сообщения, ожидающие повторной доставки.

Инцидент означает необходимость проверки ответственным. Сообщения не объявляют кражу автоматически. Исторические инциденты при установке не рассылаются. Resolve/изменения статуса пока не создают отдельные сообщения.

## Поток и гарантии

Создание инцидента и `telegram_notifications` выполняются в одной транзакции. Откат не оставляет уведомление. Уникальный `event_key` исключает повторное добавление того же события. HTTP request не ждёт внешнего Telegram.

Раз в минуту systemd запускает bounded worker внутри действующего API container. Он выбирает до 10 сообщений одной явно настроенной организации, блокирует запись `FOR UPDATE SKIP LOCKED`, отправляет JSON HTTPS request и сохраняет `SENT` только после `ok=true`, положительного `message_id` и подтверждения ожидаемого chat ID. Между попытками выдерживается 1,1 секунды; worker ограничен 45 секундами между сообщениями и network timeout 10 секунд. Большая очередь обрабатывается следующими запусками.

При отказе запись остаётся `PENDING`: задержка 30 секунд с удвоением до часа, при HTTP 429 учитывается `retry_after`. Сохраняется только ограниченный error code, без token, URL или response body. Перезапуск worker сохраняет очередь. Повторный штатный запуск не отправляет `SENT` заново. Гарантия — **at-least-once**: авария после принятия Telegram, но до commit может дать дубль; Bot API не предоставляет idempotency key.

Записи чужой организации и записи без организации не выбираются. Один production chat соответствует одной организации. Новый tenant требует отдельного явного назначения; нельзя направлять все школы в существующий чат.

## Настройка Linux production

Используется существующий защищённый `/etc/assetguard/server-monitor.env` (root, mode 600):

```dotenv
ASSETGUARD_TELEGRAM_BOT_TOKEN=<секрет бота>
ASSETGUARD_TELEGRAM_CHAT_ID=<числовой идентификатор настроенного чата>
ASSETGUARD_TELEGRAM_ORGANIZATION_ID=<UUID разрешённой организации>
ASSETGUARD_NOTIFICATION_UTC_OFFSET_HOURS=5
```

Общий monitor также использует `ASSETGUARD_BACKUP_STATUS_FILE`. Wrapper берёт публичный host из `/opt/assetguard/.env` и передаёт HTTPS URL worker. Секреты не записываются в unit, Git или документацию. Нужны применённая migration `0026_telegram_notifications`, исходящий HTTPS к api.telegram.org и работающий API container.

```bash
sudo bash /opt/assetguard/scripts/linux/install-server-notifications.sh /opt/assetguard
sudo systemctl start assetguard-notifications.service
sudo systemctl status assetguard-notifications.timer
sudo journalctl -u assetguard-notifications.service --since today
```

Контролируемый тест (каждый вызов с флагом создаёт **новое** сообщение):

```bash
sudo /usr/local/lib/assetguard-server-notifications.sh --enqueue-test
sudo /usr/local/lib/assetguard-server-notifications.sh
```

Первый запуск при пустой очереди: `sent=1, retry_scheduled=0`; второй: `sent=0`. Telegram acceptance подтверждает доставку в чат на стороне сервиса, но не прочтение человеком. Не создавайте фиктивные инциденты в production ради проверки.

## Наблюдаемость и проверка

Защищённый `/admin/operations/status` включает `notifications.pending` и `notifications.retrying`, ограниченные существующим organization/location scope. `retrying` — ещё ожидающие сообщения с хотя бы одной попыткой, а не число всех ошибок за историю. Чат настроен сервером; пользовательские экраны не показывают token. Monitor работает раз в 5 минут, неизменившиеся проблемы повторяет через 4 часа, очищает fingerprint после восстановления. Отдельное сообщение о восстановлении пока не отправляется.

Тесты проверяют реальные producer paths технического ingestion/физического обхода, rollback, уникальность событий, HTTP отказ/429, restart/retry, отсутствие повторной доставки, параллельные worker и tenant isolation. Проверка настоящей доставки и результатов deployment фиксируется отдельно в release record.

Ограничения pilot: очередь содержит описание имущества и пока не имеет автоматического retention; доступна через PostgreSQL/операционные агрегаты, UI управления очередью отсутствует. Сроки хранения и маршрутизация нескольких организаций требуют отдельного решения. Сводный monitor отслеживает число проблем Agent, поэтому замена одного проблемного ПК другим при неизменных агрегатах может не создать новый alert. Полный журнал индивидуальных переходов Agent — следующий функциональный этап.

Migration downgrade до `0025` удаляет таблицу очереди, включая недоставленные записи. До отката сохраните encrypted backup и осознанно выберите восстановление/перенос очереди. Изменений старых таблиц migration не делает.

Решение: [ADR-007](../decisions/ADR-007-telegram-outbox.md). Протокол внешнего сервиса: [Telegram Bot API](https://core.telegram.org/bots/api#sendmessage).
