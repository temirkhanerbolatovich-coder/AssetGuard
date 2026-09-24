# Windows operations

Upstream GLPI Agent устанавливается отдельно: AssetGuard не модифицирует и не форкает collector. Скрипты каталога покрывают локальную demo-эксплуатацию:

- `new-local-env.ps1` — создаёт локальные secrets;
- `start-demo.ps1` — поднимает PostgreSQL, миграции и API;
- `collect-minimal-inventory.ps1` — собирает privacy-limited JSON;
- `send-minimal-inventory.ps1` — отправляет его в authenticated gateway;
- `install-background-demo.ps1` / `uninstall-background-demo.ps1` — управляют demo Scheduled Tasks;
- `install-pilot-agent-schedule.ps1` — ставит отдельное расписание Agent на каждом pilot-компьютере; поддерживает необязательные измерения packet loss и задержки до указанной цели;
- `install-assetguard-agent-service.ps1` / `uninstall-assetguard-agent-service.ps1` — ставят upstream GLPI Agent как обычную Windows-службу с автозапуском, recovery и защищённым минимальным AssetGuard profile. Это рекомендуемый путь для pilot-PC;
- `start-free-public-demo.ps1` — поднимает контейнерный demo и временный публичный Cloudflare HTTPS URL;
- `install-quick-tunnel-watchdog.ps1` / `uninstall-quick-tunnel-watchdog.ps1` — поддерживают Quick Tunnel после сбоя и при следующем входе в Windows; текущий URL находится в `%LOCALAPPDATA%\AssetGuard\quick-tunnel.json`;
- `backup-database.ps1` / `restore-database.ps1` — создают AES-256-GCM encrypted backup, опционально копируют его на внешний диск или `rclone` remote и восстанавливают БД;
- `verify-backup-restore.ps1` — безопасно репетирует restore в отдельном одноразовом PostgreSQL контейнере, не затрагивая рабочую БД.

Скрипты не отключают TLS, не записывают secrets в исходники и не меняют baseline автоматически.

Пример для каждого компьютера пилота (после копирования репозитория и `.env` с ограниченными правами):

```powershell
.\scripts\windows\install-pilot-agent-schedule.ps1 -RepositoryRoot 'C:\AssetGuard' -GatewayUri 'https://<временный-или-постоянный-host>/internal/inventories' -NetworkTarget '1.1.1.1' -EveryHours 4
```

`NetworkTarget` измеряет только четыре ICMP-пробы: адрес цели, число ответов, потери и среднюю задержку. Скорость канала, содержимое трафика, список посещений и учётные данные не собираются.

Для primary native transport настройте установленный GLPI Agent 1.19 на `https://<host>/glpi-agent`, Basic user `assetguard`, rotating inventory secret и profile `glpi-agent-minimal-profile.cfg`. Explicit `send-minimal-inventory.ps1` остаётся fallback для автономного collection режима. Production credentials должны храниться в защищённой конфигурации агента с ограниченным ACL, а не в командном файле.

## Установка Windows-службы агента

Откройте PowerShell **от имени администратора**. Установщик при необходимости использует официальный пакет `GLPI-Project.GLPI-Agent` из WinGet, но не модифицирует код GLPI Agent. Он создаёт только `etc/conf.d/99-assetguard.cfg`: профиль отключает processes, users, software, USB и прочие не нужные для инвентаризации категории; файл доступен лишь `SYSTEM` и локальным Administrators.

```powershell
$secret = Read-Host 'Inventory secret' -AsSecureString
.\scripts\windows\install-assetguard-agent-service.ps1 `
  -GatewayUri 'https://<public-host>/glpi-agent' `
  -InventorySecret $secret
```

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

Для локального Vision demo Python environment должен быть установлен с extras `backend[dev,vision]`. Модель загружается при первом scan; demo-изображения находятся в `demo/vision/`.
