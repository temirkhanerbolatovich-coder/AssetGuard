# Локальная демонстрационная поставка MVP

## Первый запуск

1. Распакуйте release в путь с латинскими символами, например `C:\AssetGuard-MVP`.
2. Установите Docker Desktop и Python 3.12.
3. В корне проекта выполните команды из README для создания `.env`, virtual environment, зависимостей и запуска.
4. Откройте `http://127.0.0.1:8000` и возьмите admin token из `.env`.

## Демонстрация

Следуйте `docs/product/demo-scenario.md`. Для локального GLPI evidence используйте `scripts/windows/collect-minimal-inventory.ps1`; отправка в поднятый gateway: `send-minimal-inventory.ps1 -GatewayUri http://127.0.0.1:8000/internal/inventories`.

## Границы поставки

- `.env`, database volume, GLPI raw results и logs исключены из release.
- Bridge разрешает HTTP только для loopback; вне localhost требуется HTTPS.
- Vision model/weights, фотографии и RTSP не входят в MVP v0.1.

## Фоновый локальный режим

По умолчанию MVP не создаёт фоновые процессы. После проверки demo можно явно зарегистрировать две user-level Scheduled Tasks:

```powershell
pwsh -File .\scripts\windows\install-background-demo.ps1 -InventoryEveryHours 4
```

Первая поднимает API при входе пользователя, вторая запускает privacy-limited GLPI inventory каждые 4 часа. Это не Windows Service и работает только пока пользователь вошёл в Windows. Удаление задач: `pwsh -File .\scripts\windows\uninstall-background-demo.ps1`.
