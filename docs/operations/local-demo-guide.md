# Локальная демонстрационная поставка MVP

## Первый запуск

1. Распакуйте release в путь с латинскими символами, например `C:\AssetGuard-MVP`.
2. Установите Docker Desktop и Python 3.12.
3. В корне проекта выполните команды из README для создания `.env`, virtual environment, зависимостей и запуска.
4. Откройте `http://127.0.0.1:8000` и возьмите admin token из `.env`.

## Демонстрация

Следуйте `docs/product/demo-scenario.md`. Для локального GLPI evidence используйте `scripts/windows/collect-minimal-inventory.ps1`; отправка в поднятый gateway: `send-minimal-inventory.ps1 -GatewayUri http://127.0.0.1:8000/internal/inventories`.

Для полностью воспроизводимого pitch-инцидента выполните `scripts/windows/prepare-pitch-incident.ps1`. Он создаст связанный актив, baseline из двух модулей RAM и второй полный снимок без одного модуля через рабочие API. Готовый порядок показа и текст выступления находятся в `docs/product/pitch-guide.md`.

## Временный публичный доступ без VPS

Если запускаете весь Docker demo stack, используйте `pwsh -File .\scripts\windows\start-free-public-demo.ps1`. Если уже работает ваш локальный API с реальными данными, используйте `pwsh -File .\scripts\windows\start-local-quick-tunnel.ps1`: он не создаёт вторую БД и публикует именно текущий локальный контур. Оба варианта выведут временный HTTPS URL Cloudflare Quick Tunnel. Он подходит для показа 25 сентября, но URL меняется после перезапуска и не заменяет постоянный домен.

При нажатии **«QR для обхода»** Dashboard попросит вставить полученный HTTPS URL и запомнит его только в браузере. Поэтому не нужно перезапускать API и менять `.env`; QR будет открывать карточку через этот адрес после входа пользователя. `ASSETGUARD_PUBLIC_URL` остаётся fallback для постоянного домена.

Для устойчивости временного адреса на компьютере презентации один раз выполните `pwsh -File .\scripts\windows\install-quick-tunnel-watchdog.ps1`. Watchdog автоматически восстановит Tunnel при сбое и при следующем входе в Windows. После восстановления прочитайте новый URL из `%LOCALAPPDATA%\AssetGuard\quick-tunnel.json` и заново создайте QR: Quick Tunnel не сохраняет адрес между соединениями.

Для Vision загрузите `demo/vision/room-305-baseline.png`, сохраните scan как baseline и затем загрузите `demo/vision/room-305-warning.png`. Первый scan может быть медленнее: Grounding DINO weights скачиваются в локальный Hugging Face cache и модель инициализируется на CPU/GPU. Подробности находятся в `demo/vision/README.md`.

## Границы поставки

- `.env`, database volume, GLPI raw results и logs исключены из release.
- Bridge разрешает HTTP только для loopback; вне localhost требуется HTTPS.
- Demo-фотографии входят в репозиторий; runtime скачивает open-source model weights при первом Vision scan.
- RTSP, постоянное видеонаблюдение и автоматическое расписание не входят в demo MVP.

## Фоновый локальный режим

По умолчанию MVP не создаёт фоновые процессы. После проверки demo можно явно зарегистрировать две user-level Scheduled Tasks:

```powershell
pwsh -File .\scripts\windows\install-background-demo.ps1 -InventoryEveryHours 4
```

Первая поднимает API при входе пользователя, вторая запускает privacy-limited GLPI inventory каждые 4 часа. Это не Windows Service и работает только пока пользователь вошёл в Windows. Удаление задач: `pwsh -File .\scripts\windows\uninstall-background-demo.ps1`.
