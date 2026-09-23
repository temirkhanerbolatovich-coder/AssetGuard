# Бесплатный deployment AssetGuard

## Рекомендуемый контур для хакатона

AssetGuard, PostgreSQL и Grounding DINO работают на существующем Windows-компьютере в Docker. `cloudflared` создаёт исходящее соединение и выдаёт временный публичный HTTPS URL, поэтому не нужны домен, публичный IP или настройка роутера.

Требования: Docker Desktop, свободное место под PostgreSQL и model cache, доступ в Интернет для скачивания контейнеров и весов модели.

```powershell
pwsh -File .\scripts\windows\new-local-env.ps1
pwsh -File .\scripts\windows\start-free-public-demo.ps1
```

Первый запуск собирает API image с CPU-версией PyTorch и поэтому заметно дольше следующих. Локальный адрес остаётся `http://127.0.0.1:8000`; скрипт извлекает публичный `https://…trycloudflare.com` из логов туннеля.

Остановка без удаления данных:

```powershell
docker compose --env-file .env -f infra/containers/docker-compose.free-demo.yml down
```

Чтобы удалить именованные volumes, нужна отдельная осознанная команда с `--volumes`; обычная остановка данные не удаляет.

## Ограничения Quick Tunnel

- адрес меняется после пересоздания tunnel container;
- сервис предназначен для разработки и демонстраций, без SLA;
- нельзя использовать этот адрес как постоянный target для парка GLPI Agent;
- публичный URL открывает login/API всему Интернету, поэтому используются случайные secrets, rate limit и только тестовые данные;
- после демонстрации стек следует остановить.

Для постоянного deployment используйте production Compose, стабильный DNS name и Caddy/Let’s Encrypt. Cloudflare Quick Tunnels документированы как testing-only: <https://developers.cloudflare.com/cloudflare-one/networks/connectors/cloudflare-tunnel/do-more-with-tunnels/trycloudflare/>.

## Бесплатный encrypted backup

Backup по умолчанию шифруется AES-256-GCM; незашифрованный SQL существует только во временном файле и удаляется после операции. Пароль можно ввести в скрытом prompt:

```powershell
pwsh -File .\scripts\windows\backup-database.ps1
```

Копирование зашифрованного файла на внешний диск или в синхронизируемую папку:

```powershell
pwsh -File .\scripts\windows\backup-database.ps1 -OffsiteTarget 'E:\AssetGuard-Backups'
```

Для Backblaze B2 или Cloudflare R2 сначала настройте бесплатный `rclone` remote, затем передайте путь вида `remote:bucket/folder`:

```powershell
pwsh -File .\scripts\windows\backup-database.ps1 -OffsiteTarget 'b2:assetguard-backups'
```

Для автоматического задания передайте пароль через защищённую переменную процесса `ASSETGUARD_BACKUP_PASSPHRASE`; не добавляйте его в `.env`, Git или текст Scheduled Task. Восстановление запрашивает тот же пароль:

```powershell
pwsh -File .\scripts\windows\restore-database.ps1 -BackupFile .local\backups\assetguard-YYYYMMDD-HHMMSS.sql.agbackup
```

Пароль нельзя восстановить. Храните его отдельно от backup и обязательно выполните пробное восстановление до использования схемы как единственной копии.

## Бесплатные CI и E2E

Workflow GitHub Actions запускает API/integration tests, Chromium E2E через Playwright и проверку обоих Compose-файлов. Standard runners бесплатны для публичного репозитория. Локальный браузерный тест:

```powershell
backend\.venv\Scripts\python.exe -m pip install -e 'backend[dev,e2e]'
backend\.venv\Scripts\python.exe -m playwright install chromium
$env:ASSETGUARD_RUN_BROWSER_E2E='1'
backend\.venv\Scripts\python.exe -m pytest -q backend\tests\e2e
```

Перед локальным E2E API должен работать на `http://127.0.0.1:8000` с текущим `.env`.
