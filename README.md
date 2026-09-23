# AssetGuard

AssetGuard — MVP системы непрерывного контроля компьютерных активов. Она принимает инвентаризацию от неизменённого GLPI Agent, сохраняет исходный payload, строит нормализованные снимки оборудования, сравнивает их с явно подтверждённым baseline и ведёт объяснимую историю изменений и решений.

## Статус

Готов демонстрационный MVP v0.1: FastAPI backend, PostgreSQL migrations, browser dashboard, baseline/change/incident workflow, GLPI Agent minimal privacy profile и AssetGuard Vision. Vision поддерживает загрузку JPEG/PNG, Grounding DINO object detection, bounding boxes, подсчёт объектов, room baseline, повторное сравнение и начальный статус `WARNING`.

## Быстрый запуск на Windows

Нужны Docker Desktop и Python 3.12. Распакуйте проект в путь без кириллических символов (например `C:\AssetGuard-MVP`), затем в корне выполните:

```powershell
pwsh -File .\scripts\windows\new-local-env.ps1
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e 'backend[dev,vision]'
pwsh -File .\scripts\windows\start-demo.ps1
```

Откройте http://127.0.0.1:8000. Для bootstrap можно использовать admin token из локального `.env`; затем рекомендуется создать named ADMIN/VIEWER пользователя и входить по username/password. Сессии можно завершать и отзывать, secrets не включаются в исходники или release archive.

GitHub Actions проверяет migrations/tests на PostgreSQL, зависимости Python, JavaScript syntax и production Compose. Локально актуальный набор содержит 13 tests.

Production Compose также включает Vision dependencies, persistent image storage и model cache; ограничения и настройки описаны в `docs/operations/production-deployment.md`.

## Демонстрация Vision

В блоке **AssetGuard Vision** укажите помещение и загрузите `demo/vision/room-305-baseline.png`. После обработки нажмите **Сохранить baseline**, затем загрузите `demo/vision/room-305-warning.png`: на втором кадре удалён принтер, поэтому сравнение показывает расхождение и `WARNING`. Первый запуск загружает/инициализирует модель и на CPU может занять больше времени; следующие scans выполняются уже на прогретой модели.

## Главный принцип

Новый snapshot не становится baseline автоматически. Отсутствие данных в частичной инвентаризации не означает, что компонент удалён.

## Навигация

- [Сохранённые требования MVP](ASSETGUARD_MVP_v0.1_REQUIREMENTS.md)
- [Анализ требований](ASSETGUARD_MVP_v0.1_ANALYSIS.md)
- [Исследование open-source основы](ASSETGUARD_TECHNICAL_RESEARCH.md)
- [Карта документации](docs/README.md)
- [Чек-лист завершения MVP](docs/product/mvp-completion-checklist.md)
- [Локальная demo-поставка](docs/operations/local-demo-guide.md)
- [Production deployment и recovery](docs/operations/production-deployment.md)
- [GLPI minimal profile spike](docs/integration/glpi-agent-minimal-profile-spike.md)
- [Требования AssetGuard Vision](docs/product/assetguard-vision-requirements.md)
- [Минимальная интеграция AssetGuard Vision](docs/architecture/assetguard-vision-integration-analysis.md)

## Будущий вертикальный поток

`Inventory → Raw evidence → Snapshot → Explicit baseline → Change Detection → Incident → Decision → History`

## Границы MVP

AssetGuard не является форком GLPI, custom Windows agent, helpdesk или системой автоматического определения краж. GLPI Agent остаётся collector, а AssetGuard владеет raw inventory, snapshots, baseline, events, incidents и history.
