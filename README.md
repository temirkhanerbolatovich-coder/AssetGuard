# AssetGuard

[![CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/temirkhanerbolatovich-coder/AssetGuard?include_prereleases)](https://github.com/temirkhanerbolatovich-coder/AssetGuard/releases)

AssetGuard — система учёта и контролируемой инвентаризации школьного имущества. Она объединяет реестр по организациям и кабинетам, технические данные Windows-компьютеров, явные эталоны оборудования, объяснимые инциденты, физические обходы, импорт/экспорт и экспериментальный Vision-контур.

Система принимает данные неизменённого GLPI Agent 1.19/1.20, сохраняет исходный payload как immutable evidence, строит нормализованный snapshot и сравнивает его только с явно подтверждённым baseline. Частичная инвентаризация не считается доказательством удаления компонента.

## Текущий статус

Статус проекта: **рабочий pilot MVP; не готов к массовому multi-school rollout**.

Подтверждено кодом, тестами или выполненной эксплуатационной проверкой:

- FastAPI, PostgreSQL 17, SQLAlchemy и Alembic migrations до `0026_telegram_notifications`;
- browser dashboard, реестр имущества, структура `организация → корпус → этаж → кабинет`;
- native GLPI XML transport и JSON bridge;
- raw inventory, snapshots, explicit baseline, changes, incidents и append-only history;
- отдельные Agent credentials, отзыв ключа и подтверждаемое re-enrolment после переустановки Windows;
- физический обход кабинета, перемещение, списание и PDF-акты;
- Excel/PDF import/export, локальный OCR и QR карточки;
- tenant/location authorization matrix для 60 защищённых admin operations;
- production HTTPS deployment, encrypted PostgreSQL backup в Cloudflare R2 и isolated restore rehearsal;
- CI, dependency audit, secret scanning и browser E2E.

До реального масштабирования остаются fleet test на 3–5 ПК, подписанный Windows installer, управляемое обновление/rollback Agent, отключение legacy shared credentials, политика хранения данных, backup Vision-фотографий и дополнительная multi-school проверка.

Актуальная точка правды: [полный чек-лист проекта](docs/product/current-project-checklist.md). Последний опубликованный pilot installer — [`v0.1.6`](https://github.com/temirkhanerbolatovich-coder/AssetGuard/releases/tag/v0.1.6); `0.1.7` с version reporting и re-enrolment пока собран только для контролируемой проверки и не подписан.

Стабилизация 2026-10-04 опубликована и развёрнута на production из application commit `93ff8ed`: 80 backend tests, 2 browser E2E и ручной GitHub real-model smoke (23 detections) прошли. Закрыты scope ошибки native Agent и Excel/PDF import, age-based stale counters, monitor recovery/retry и структурированный количественный импорт с сохранением остатков после актов. Серверные UI/API/schema согласованы на `0025`; backup, migration/recovery rehearsal и Telegram acceptance/dedup проверены. Подробности: [протокол выкладки](outputs/assetguard-release-2026-10-04.md). Следующий этап — fleet test на 3–5 реальных ПК; installer `0.1.7` пока не опубликован.

## Архитектура

Новые технические и физические инциденты помещаются в транзакционную Telegram-очередь; отдельный worker отправляет их в явно назначенный чат организации с retry и проверкой acceptance. Проблемы Agent и сервера отслеживает существующий monitor. [Настройка и гарантии доставки](docs/features/telegram-notifications.md), [план UI/UX](docs/product/ui-ux-modernization-spec.md).

```text
GLPI Agent / JSON bridge
          │ HTTPS
          ▼
       Caddy
          ▼
FastAPI modular monolith ─────► Vision files/model cache
          │
          ▼
     PostgreSQL 17 ───────────► encrypted backup ─► Cloudflare R2
```

Основной поток:

`Inventory → Raw evidence → Snapshot → Explicit baseline → Change → Incident → Decision → History`

AssetGuard не является форком GLPI, custom collector, helpdesk, remote desktop или системой автоматического определения кражи. GLPI Agent остаётся внешним сборщиком; `WARNING` и `OFFLINE` означают необходимость проверки человеком.

## Быстрый локальный запуск

Требования: Windows, Docker Desktop, PowerShell 7 и Python 3.12. Для Python рекомендуется путь без кириллицы.

```powershell
pwsh -File .\scripts\windows\new-local-env.ps1
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e 'backend[dev,vision]'
pwsh -File .\scripts\windows\start-demo.ps1
```

Откройте <http://127.0.0.1:8000>. Bootstrap token берётся из локального `.env`; после первого входа создайте именованного пользователя. Не используйте production credentials в локальной среде и не добавляйте `.env` в Git.

Для временной публичной демонстрации:

```powershell
pwsh -File .\scripts\windows\start-free-public-demo.ps1
```

Cloudflare Quick Tunnel предназначен только для демонстрации: URL меняется и не подходит для постоянной установки Agent.

## Тестирование

Backend-тесты запускаются из каталога `backend`, чтобы Alembic использовал правильную конфигурацию:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m pytest -q
Pop-Location

node --check frontend/app.js
git diff --check
```

Текущий подтверждённый набор: **50 unit/integration tests и 2 browser E2E**. Каждый backend-запуск создаёт отдельную PostgreSQL database, применяет migrations до `head`, очищает состояние между тестами и удаляет базу после завершения.

## Windows Agent

Новые установки закреплены на upstream GLPI Agent `1.20`. Installer:

- устанавливает службу с автозапуском и recovery;
- применяет privacy-limited profile;
- использует отдельный username/secret для каждого компьютера;
- сообщает версии installer и Agent;
- пишет локальный lifecycle log без секретов;
- поддерживает подтверждаемое восстановление после переустановки Windows по SMBIOS UUID.

Подробности: [Windows operations](scripts/windows/README.md) и [fleet test](docs/operations/agent-fleet-pilot.md). Неподписанный EXE допустим только для ограниченного внутреннего пилота.

## Production и восстановление

Production topology публикует только Caddy на 80/443; API и PostgreSQL находятся во внутренней Docker-сети. PostgreSQL backup шифруется AES-256-GCM, отправляется в R2 и проверяется восстановлением в disposable database. Vision volume пока не включён в этот backup.

- [Deployment overview](docs/deployment/README.md)
- [Production deployment and recovery](docs/operations/production-deployment.md)
- [Observability](docs/operations/observability.md)
- [Security model](docs/security/security-model.md)

## Документация

Полная карта находится в [docs/README.md](docs/README.md). Основные документы:

- [архитектура](docs/architecture/overview.md) и [потоки данных](docs/architecture/data-flow.md);
- [API boundaries](docs/api/README.md);
- [реализованные возможности](docs/features/README.md);
- [ADR](docs/decisions/README.md);
- [стратегия тестирования](docs/testing/testing-strategy.md);
- [production roadmap](docs/product/production-readiness-roadmap.md);
- [технический долг](docs/technical-debt.md);
- [история релизов и unreleased changes](CHANGELOG.md).

Исходные требования, исследования и старые планы сохранены как исторические документы. При расхождении приоритет имеют текущий код, executable tests, migrations и документы, помеченные как актуальные в карте документации.

## Безопасность и ограничения

- Не публикуйте `.env`, Agent secrets, backup passphrase, R2 keys или Telegram token.
- Не отключайте TLS verification для постоянного Agent endpoint.
- Не принимайте новый snapshot как baseline автоматически.
- Не разворачивайте Vision production без retention policy и отдельного backup фотографий.
- Не распространяйте installer массово до code signing и проверенного rollback.

Лицензионная модель проекта пока не зафиксирована отдельным `LICENSE`; до её определения репозиторий нельзя считать разрешением на свободное переиспользование.
