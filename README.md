# AssetGuard

AssetGuard — MVP системы непрерывного контроля компьютерных активов. Она принимает инвентаризацию от неизменённого GLPI Agent, сохраняет исходный payload, строит нормализованные снимки оборудования, сравнивает их с явно подтверждённым baseline и ведёт объяснимую историю изменений и решений.

## Статус

Готов локальный демонстрационный MVP v0.1: FastAPI backend, PostgreSQL migrations, browser dashboard, baseline/change/incident workflow и GLPI Agent minimal privacy profile. Vision Inventory в эту поставку не входит.

## Быстрый запуск на Windows

Нужны Docker Desktop и Python 3.12. Распакуйте проект в путь без кириллических символов (например `C:\AssetGuard-MVP`), затем в корне выполните:

```powershell
pwsh -File .\scripts\windows\new-local-env.ps1
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e 'backend[dev]'
pwsh -File .\scripts\windows\start-demo.ps1
```

Откройте http://127.0.0.1:8000. Admin token берётся из локального `.env`; он не включается в исходники или release archive.

## Главный принцип

Новый snapshot не становится baseline автоматически. Отсутствие данных в частичной инвентаризации не означает, что компонент удалён.

## Навигация

- [Сохранённые требования MVP](ASSETGUARD_MVP_v0.1_REQUIREMENTS.md)
- [Анализ требований](ASSETGUARD_MVP_v0.1_ANALYSIS.md)
- [Исследование open-source основы](ASSETGUARD_TECHNICAL_RESEARCH.md)
- [Карта документации](docs/README.md)
- [Локальная demo-поставка](docs/operations/local-demo-guide.md)
- [GLPI minimal profile spike](docs/integration/glpi-agent-minimal-profile-spike.md)

## Будущий вертикальный поток

`Inventory → Raw evidence → Snapshot → Explicit baseline → Change Detection → Incident → Decision → History`

## Границы MVP

AssetGuard не является форком GLPI, custom Windows agent, helpdesk или системой автоматического определения краж. GLPI Agent остаётся collector, а AssetGuard владеет raw inventory, snapshots, baseline, events, incidents и history.
