# Windows operations

Upstream GLPI Agent устанавливается отдельно: AssetGuard не модифицирует и не форкает collector. Скрипты каталога покрывают локальную demo-эксплуатацию:

- `new-local-env.ps1` — создаёт локальные secrets;
- `start-demo.ps1` — поднимает PostgreSQL, миграции и API;
- `collect-minimal-inventory.ps1` — собирает privacy-limited JSON;
- `send-minimal-inventory.ps1` — отправляет его в authenticated gateway;
- `install-background-demo.ps1` / `uninstall-background-demo.ps1` — управляют demo Scheduled Tasks;
- `install-pilot-agent-schedule.ps1` — ставит отдельное расписание Agent на каждом pilot-компьютере; поддерживает необязательные измерения packet loss и задержки до указанной цели;
- `start-free-public-demo.ps1` — поднимает контейнерный demo и временный публичный Cloudflare HTTPS URL;
- `install-quick-tunnel-watchdog.ps1` / `uninstall-quick-tunnel-watchdog.ps1` — поддерживают Quick Tunnel после сбоя и при следующем входе в Windows; текущий URL находится в `%LOCALAPPDATA%\AssetGuard\quick-tunnel.json`;
- `backup-database.ps1` / `restore-database.ps1` — создают AES-256-GCM encrypted backup, опционально копируют его на внешний диск или `rclone` remote и восстанавливают БД.

Скрипты не отключают TLS, не записывают secrets в исходники и не меняют baseline автоматически.

Пример для каждого компьютера пилота (после копирования репозитория и `.env` с ограниченными правами):

```powershell
.\scripts\windows\install-pilot-agent-schedule.ps1 -RepositoryRoot 'C:\AssetGuard' -GatewayUri 'https://<временный-или-постоянный-host>/internal/inventories' -NetworkTarget '1.1.1.1' -EveryHours 4
```

`NetworkTarget` измеряет только четыре ICMP-пробы: адрес цели, число ответов, потери и среднюю задержку. Скорость канала, содержимое трафика, список посещений и учётные данные не собираются.

Для primary native transport настройте установленный GLPI Agent 1.19 на `https://<host>/glpi-agent`, Basic user `assetguard`, rotating inventory secret и profile `glpi-agent-minimal-profile.cfg`. Explicit `send-minimal-inventory.ps1` остаётся fallback для автономного collection режима. Production credentials должны храниться в защищённой конфигурации агента с ограниченным ACL, а не в командном файле.

Для локального Vision demo Python environment должен быть установлен с extras `backend[dev,vision]`. Модель загружается при первом scan; demo-изображения находятся в `demo/vision/`.
