# AssetGuard — остановка production

Подтверждено **2026-10-10 21:44:03 UTC+5**; контейнеры остановлены в **21:40:20 UTC+5**. Владелец запросил остановку AssetGuard и Telegram-уведомлений, затем подтвердил Oracle Cloud как целевой сервер и обычную перезагрузку VM для восстановления доступа.

## Выполнено и проверено

- Сервер `assetguard-prod`, Oracle Cloud `ap-tokyo-1`, публичный адрес `161.33.158.204` подтверждён в Console. SSH и Cloud Agent до перезагрузки не отвечали. Диагностический Run Command не дал ответа; на его отмену отправлен запрос. Команда не изменяла систему.
- Обычная перезагрузка VM согласована из-за возможного прерывания TimScheduleBot. После восстановления SSH остановлен только AssetGuard.
- `assetguard-monitor`, `assetguard-notifications`, `assetguard-backup`, `assetguard-restore-rehearsal`, `assetguard-duckdns`: все пять timers disabled/inactive; services inactive. Автоматические Telegram alerts и доставка outbox выключены. AssetGuard cron entries у root/ubuntu отсутствуют.
- Локальная Windows task `AssetGuard Telegram operations monitor` остановлена и **Disabled**. Другие локальные demo/Agent/backup tasks не менялись.
- Docker Compose `down` без `--volumes` удалил только API, PostgreSQL, Caddy и проектную сеть. Контейнеров проекта осталось **0**; **5** Docker volumes проверены и сохранены. Checkout, `.env`, Docker images и резервные копии сохранены. Credentials не удалялись и не менялись.
- Проверено наличие **47** локальных encrypted backups. Последний сохранённый файл — `assetguard-production-20261010-020003.sql.agbackup`. Новый backup/restore при остановке не запускался.
- TimScheduleBot после остановки AssetGuard — **active/running**, `ExecMainStatus=0`, запущен после перезагрузки в `2026-10-10 16:38:49 UTC`. Его код и конфигурация не менялись.
- Публичные HTTP/HTTPS listeners отсутствуют; внешняя проверка `/health/ready` вернула отказ соединения, HTTP `000`. Production UI/API и приём Agent reports недоступны.
- Render проверен: AssetGuard отсутствует в подключённом workspace и в Main's workspace второго аккаунта. Сервисы DataHub-Uni.kz, VKO Internet Monitoring и LifecycleKASE не отключались.

Проверка: Bash syntax, runtime/container labels, все пять unit states, retained volumes/images/backups, Windows task, отсутствие HTTP listeners, внешний HTTPS и состояние TimScheduleBot. Application code и schema не менялись; новый прогон API/E2E и restore не выполнялся. Прежняя application acceptance `7c45435` остаётся историческим результатом. Docker image сохранена: `sha256:1a98957a3ef6829a3281d32c5e9130157a4e73feff730e2e4a165da7902beda1`.

## Возобновление

Только после нового запроса владельца. Для запуска сохранённой image без rebuild:

```bash
cd /opt/assetguard
sudo docker compose --env-file .env \
  -f infra/containers/docker-compose.production.yml \
  -f infra/containers/docker-compose.oracle-free.yml up -d --no-build
```

Затем проверить health/readiness и schema. Backup/restore и DuckDNS timers можно включить при возобновлении эксплуатации. Server monitor/notification timers и локальную Telegram task включать только при явном разрешении возобновить Telegram: сохранённая outbox может содержать ожидающие записи. Установленные PC Agents не удалялись; Agent 0.1.8 при недоступности сервера сохраняет отчёты в локальной ограниченной очереди.
