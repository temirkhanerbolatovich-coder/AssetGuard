# Windows operations

Upstream GLPI Agent устанавливается отдельно: AssetGuard не модифицирует и не форкает collector. Скрипты каталога покрывают локальную demo-эксплуатацию:

- `new-local-env.ps1` — создаёт локальные secrets;
- `start-demo.ps1` — поднимает PostgreSQL, миграции и API;
- `collect-minimal-inventory.ps1` — собирает privacy-limited JSON;
- `send-minimal-inventory.ps1` — отправляет его в authenticated gateway;
- `install-background-demo.ps1` / `uninstall-background-demo.ps1` — управляют demo Scheduled Tasks;
- `install-pilot-agent-schedule.ps1` — ставит отдельное расписание Agent на каждом pilot-компьютере; поддерживает необязательные измерения packet loss и задержки до указанной цели;
- `install-assetguard-agent-service.ps1` / `uninstall-assetguard-agent-service.ps1` — ставят upstream GLPI Agent как обычную Windows-службу с автозапуском, recovery и защищённым минимальным AssetGuard profile. Это рекомендуемый путь для pilot-PC;
- `build-agent-installer.ps1` — собирает `AssetGuard-Agent-Setup-0.1.1.exe`: мастер установки для передачи на другие Windows-компьютеры;
- `start-free-public-demo.ps1` — поднимает контейнерный demo и временный публичный Cloudflare HTTPS URL;
- `install-quick-tunnel-watchdog.ps1` / `uninstall-quick-tunnel-watchdog.ps1` — поддерживают Quick Tunnel после сбоя и при следующем входе в Windows; текущий URL находится в `%LOCALAPPDATA%\AssetGuard\quick-tunnel.json`;
- `backup-database.ps1` / `restore-database.ps1` — создают AES-256-GCM encrypted backup, опционально копируют его на внешний диск или `rclone` remote и восстанавливают БД;
- `verify-backup-restore.ps1` — безопасно репетирует restore в отдельном одноразовом PostgreSQL контейнере, не затрагивая рабочую БД.
- `set-backup-passphrase.ps1` / `install-backup-schedule.ps1` — сохраняют пароль backup через Windows DPAPI и устанавливают daily backup + weekly isolated restore rehearsal для текущего Windows-пользователя.
- `set-telegram-credentials.ps1` / `send-operations-telegram-alert.ps1` / `install-operations-telegram-monitor.ps1` — сохраняют Telegram credential в DPAPI, проверяют offline Agent, failed ingest, конфликты идентификации и место на диске, затем отправляют deduplicated alert.

Скрипты не отключают TLS, не записывают secrets в исходники и не меняют baseline автоматически.

Пример для каждого компьютера пилота (после копирования репозитория и `.env` с ограниченными правами):

```powershell
.\scripts\windows\install-pilot-agent-schedule.ps1 -RepositoryRoot 'C:\AssetGuard' -GatewayUri 'https://<временный-или-постоянный-host>/internal/inventories' -NetworkTarget '1.1.1.1' -EveryHours 4
```

`NetworkTarget` измеряет только четыре ICMP-пробы: адрес цели, число ответов, потери и среднюю задержку. Скорость канала, содержимое трафика, список посещений и учётные данные не собираются.

Для primary native transport настройте установленный GLPI Agent 1.19 на `https://<host>/glpi-agent`, Basic user `assetguard`, rotating inventory secret и profile `glpi-agent-minimal-profile.cfg`. Explicit `send-minimal-inventory.ps1` остаётся fallback для автономного collection режима. Production credentials должны храниться в защищённой конфигурации агента с ограниченным ACL, а не в командном файле.

## Установка Windows-службы агента

## Графический установщик для других компьютеров

Для передачи Agent на другие компьютеры соберите один установочный файл на компьютере разработчика. Он **не содержит** `.env`, backup, PDF, уже собранные инвентаризации или ключи других устройств. На целевом ПК мастер запросит уникальные логин и ключ именно этого устройства, установит официальный GLPI Agent через WinGet, включит службу и после установки удалит временный файл с ключом.

Один раз установите бесплатный Inno Setup 6 на компьютере разработчика:

```powershell
winget install --id JRSoftware.InnoSetup --exact --source winget
```

Соберите EXE:

```powershell
.\scripts\windows\build-agent-installer.ps1
```

Готовый файл появится в `installer-output\AssetGuard-Agent-Setup-0.1.1.exe` (эта папка намеренно не попадает в Git). Рядом передайте SHA-256, который покажет команда сборки. Для production-пилота перед распространением подпишите EXE сертификатом code signing: без подписи Windows SmartScreen может попросить дополнительное подтверждение.

На каждом целевом ПК:

1. В админ-панели создайте отдельные Agent credentials. Логин и ключ показываются один раз.
2. Запустите EXE **от имени администратора**.
3. Укажите `https://ваш-домен/glpi-agent`, уникальный логин и ключ. Для постоянной установки не используйте `trycloudflare.com`.
4. Оставьте включённой первую инвентаризацию, затем откройте карточку устройства в AssetGuard и убедитесь, что endpoint появился.

Установщик требует Windows x64, доступ к интернету и WinGet. На ПК без WinGet сначала установите официальный GLPI Agent 1.19 вручную; затем можно выполнить обычный service-скрипт с параметром `-SkipUpstreamInstall`.

Откройте PowerShell **от имени администратора**. Установщик при необходимости использует официальный пакет `GLPI-Project.GLPI-Agent` из WinGet, но не модифицирует код GLPI Agent. Он создаёт только `etc/conf.d/99-assetguard.cfg`: профиль отключает processes, users, software, USB и прочие не нужные для инвентаризации категории; файл доступен лишь `SYSTEM` и локальным Administrators.

```powershell
$secret = Read-Host 'Inventory secret' -AsSecureString
.\scripts\windows\install-assetguard-agent-service.ps1 `
  -GatewayUri 'https://<public-host>/glpi-agent' `
  -InventorySecret $secret
```

Для нового per-device credential сначала создайте его через `POST /admin/agent-credentials` под ADMIN token. API вернёт `username` и `secret` только один раз; передайте их установщику как `-AgentUsername` и `-InventorySecret`. После первого inventory credential автоматически привяжется к endpoint; отзыв через `POST /admin/agent-credentials/{id}/revoke` сразу запретит новые отправки этого Agent.

В обычном сценарии API больше не нужен: войдите в Dashboard как администратор школы и откройте раздел **«Подключить компьютеры»**. Нажмите **«Создать ключ для компьютера»**, скопируйте появившиеся логин и ключ в мастер установки. В списке раздела статус **«Ожидает установку»** сменится на **«Подключён к компьютеру»** после первой инвентаризации; оттуда же ключ можно отозвать.

Служба `GLPI Agent` запускается автоматически при включении Windows и перезапускается при трёх последовательных сбоях. Обычный пользователь не может остановить или отредактировать её; администратор может — это намеренная и безопасная модель Windows. Для немедленной первой отправки добавьте `-RunInventoryNow`.

До покупки домена для короткой демонстрации допустим действующий Quick Tunnel, но адрес меняется после перезапуска туннеля:

```powershell
.\scripts\windows\install-assetguard-agent-service.ps1 `
  -GatewayUri 'https://<current>.trycloudflare.com/glpi-agent' `
  -InventorySecret $secret -AllowTemporaryTunnel -RunInventoryNow
```

Удаление отключает службу и стирает **только** AssetGuard-конфиг вместе с credential. Пакет GLPI Agent остаётся в системе; для его явного удаления передайте `-RemoveUpstreamAgent`.

```powershell
.\scripts\windows\uninstall-assetguard-agent-service.ps1
```

## Проверка восстановления backup

Сначала создайте обычный encrypted backup, затем передайте тот же пароль скрипту проверки. Скрипт расшифровывает файл во временную директорию, поднимает изолированный PostgreSQL без открытых портов, восстанавливает SQL, проверяет Alembic revision и количество ключевых сущностей, а затем удаляет контейнер и plaintext. Рабочая база не используется для записи.

```powershell
$passphrase = Read-Host 'Backup passphrase' -AsSecureString
.\scripts\windows\backup-database.ps1 -Passphrase $passphrase
.\scripts\windows\verify-backup-restore.ps1 `
  -BackupFile .\.local\backups\assetguard-YYYYMMDD-HHMMSS.sql.agbackup `
  -Passphrase $passphrase -CompareWithCurrentDatabase
```

`-CompareWithCurrentDatabase` нужен только для свежесозданного backup: он read-only сравнивает количество восстановленных assets, endpoints, inventories, snapshots, incidents и Vision scans с текущей БД. Для старого off-site backup запускайте без этого флага — старый снимок может корректно отличаться от сегодняшних данных.

## Автоматический backup и rehearsal

На pilot-компьютере с запущенным Docker Desktop сначала один раз сохраните пароль. Это DPAPI-blob: он читается только этим Windows-пользователем на этом компьютере и не передаётся в Task Scheduler как открытый аргумент.

```powershell
.\scripts\windows\set-backup-passphrase.ps1
.\scripts\windows\install-backup-schedule.ps1 -BackupTime '02:00' -RehearsalTime '03:00'
```

Появятся две задачи: ежедневный `AssetGuard Daily Encrypted Backup` и воскресный `AssetGuard Weekly Restore Rehearsal`. Они запускаются лишь когда данный пользователь вошёл в Windows — это осознанное ограничение desktop-pilot, потому что и Docker Desktop, и DPAPI принадлежат интерактивному пользователю. Для постоянного сервера следующим шагом нужен отдельный service account и secret manager.

## Уведомления в Telegram

1. Создайте бота через `@BotFather`, получите token и начните диалог с ботом (или добавьте его в закрытую группу).
2. Получите numeric `chat_id` через `getUpdates` после первого сообщения боту. Token нельзя пересылать в чат или коммитить в Git.
3. Рекомендуемый вариант — сохранить token с Windows DPAPI, не добавляя его даже в локальный `.env`:

```powershell
$token = Read-Host 'Telegram bot token' -AsSecureString
.\scripts\windows\set-telegram-credentials.ps1 -BotToken $token -ChatId '<chat_id>'
```

Альтернативно можно вписать только в локальный `.env`:

```dotenv
ASSETGUARD_TELEGRAM_BOT_TOKEN=<token>
ASSETGUARD_TELEGRAM_CHAT_ID=<chat_id>
```

4. Проверьте доставку и установите монитор:

```powershell
.\scripts\windows\send-operations-telegram-alert.ps1 -SendTest
.\scripts\windows\install-operations-telegram-monitor.ps1 -EveryMinutes 60
```

Монитор молчит, когда всё в норме. При сохранении одинаковой проблемы повторное сообщение придёт не чаще чем раз в четыре часа; это защищает чат от спама. Telegram Bot API принимает HTTPS-запросы к `sendMessage`; скрипт использует JSON POST и проверяет поле `ok` в ответе. [Официальная документация Telegram](https://core.telegram.org/bots/api#sendmessage).

Для локального Vision demo Python environment должен быть установлен с extras `backend[dev,vision]`. Модель загружается при первом scan; demo-изображения находятся в `demo/vision/`.
