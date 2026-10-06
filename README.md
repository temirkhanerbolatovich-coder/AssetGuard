# AssetGuard

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](docs/product/current-project-checklist.md), [аудит](docs/quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

[![CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/workflows/ci.yml/badge.svg)](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/workflows/ci.yml)
[![Release](https://img.shields.io/github/v/release/temirkhanerbolatovich-coder/AssetGuard?include_prereleases)](https://github.com/temirkhanerbolatovich-coder/AssetGuard/releases)

AssetGuard — система учёта и контролируемой инвентаризации школьного имущества. Она объединяет реестр по кабинетам, технические отчёты Windows-компьютеров, подтверждённые эталоны, объяснимые инциденты, физические обходы, импорт/экспорт и экспериментальную проверку по фото.

GLPI Agent 1.19/1.20 остаётся внешним неизменённым сборщиком. AssetGuard сохраняет исходный payload, нормализует hardware snapshot и сравнивает его с явно принятым baseline. Частичный отчёт не считается доказательством удаления компонента; решение по расхождению принимает человек.

## Текущее состояние

На **6 октября 2026 года** это **рабочий pilot MVP**. Массовое внедрение в нескольких школах требует дополнительных проверок.

| Область | Подтверждённое состояние |
| --- | --- |
| Git | До этой актуализации local `main`, GitHub `main` и server checkout совпадали на `dca5a86` |
| Production | Oracle Cloud VM, Docker Compose + Caddy; application `f4f56e7`, HTTPS [публичный сервер](https://assetguard-temirkhan.duckdns.org/) |
| БД | PostgreSQL 17; 26 Alembic migrations, head `0026_telegram_notifications` |
| API | 73 HTTP operations на 66 путях; 64 защищённые admin operations на 57 путях |
| Проверки | Свежий локальный прогон: **170 passed** — 148 backend + 22 browser E2E; JS, scripts и Compose проверены |
| CI | Application и documentation CI на опубликованных SHA — success; изменения этого аудита пока локальные |
| Agent | Последний опубликованный prerelease installer — `v0.1.6`; собранный `0.1.8` — неподписанный pilot candidate |
| Восстановление | R2 backup и isolated restore на schema `0026` подтверждены протоколом 6 октября и текущим состоянием server jobs |

Работают:

- Ledger UI: обзор, имущество, единый центр технических/физических инцидентов, кабинеты и контекстное администрирование;
- индивидуальный и групповой учёт, структура `организация → корпус → этаж → кабинет`, named users, sessions и location grants;
- native GLPI XML и JSON bridge, immutable raw evidence, snapshots, explicit baseline, changes и история решений;
- отдельные Agent credentials, revoke и approved re-enrolment с сохранением endpoint;
- физический обход с проверкой итога, перемещение/списание и PDF-акты;
- Excel/PDF preview/apply, OCR, selective import и сохранение остатков после учётных актов;
- QR имущества и кабинета, запуск обхода, camera scan при поддержке браузера, ручной ввод и черновик в текущей сессии;
- транзакционная очередь Telegram-инцидентов, отдельный worker и monitor сервера/Agent;
- encrypted PostgreSQL backup в Cloudflare R2, isolated restore и systemd timers;
- локальный Vision photo workflow; тяжёлый inference на Oracle Free выключен.

После просмотра сайта локально исправлены свежесть Agent во всех экранах, состояния без Agent/до первого отчёта и ложное предупреждение о `GLPI-Agent_v1.20`. Код и документация проверены; эти правки ещё не опубликованы и не выложены на production. [Протокол и снимки](outputs/assetguard-agent-status-fixes-2026-10-06/report.md).

Главные открытые задачи: Agent 0.1.8 на 3–5 реальных ПК, code signing и проверенный update/rollback, data governance/retention, onboarding и эксплуатационная изоляция двух организаций, отказ от legacy shared credentials, staging/failover и ручная UI-приёмка.

Подробности: [актуальный чек-лист](docs/product/current-project-checklist.md), [полный аудит](docs/quality/project-audit-2026-10-06.md), [roadmap](docs/product/production-readiness-roadmap.md). Старые даты, SHA и тестовые числа в release records относятся к соответствующим этапам.

## Архитектура

```text
GLPI local collector → Windows SYSTEM task / durable FIFO → HTTPS
JSON bridge / browser                                  → Caddy
                                                          ↓
                                              FastAPI modular monolith
                                                  ↓              ↓
                                             PostgreSQL     Vision files/cache
                                                  ↓          (local demo)
                                      Telegram outbox → worker → Telegram
                                                  ↓
                                   encrypted SQL backup → Cloudflare R2
```

Основной поток: `Inventory → Raw evidence → Snapshot → Explicit baseline → Change → Incident → Decision → History`.

Состав модулей и границы: [архитектура](docs/architecture/overview.md), [потоки данных](docs/architecture/data-flow.md), [API](docs/api/README.md). Hardware collection, QR-обход и Vision являются разными источниками наблюдений.

## Быстрый локальный запуск

Требования: Windows, Docker Desktop, PowerShell 7 и Python **3.12**. Используйте ASCII-путь checkout для Python editable install. Локальный запуск на другом OS возможен через Compose; Windows Agent требует Windows x64 и прав администратора.

```powershell
pwsh -File .\scripts\windows\new-local-env.ps1
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e 'backend[dev]'
pwsh -File .\scripts\windows\start-demo.ps1
```

Откройте [локальный интерфейс](http://127.0.0.1:8000). Bootstrap token берётся из локального `.env`; затем создайте named user и назначения. Секреты production для локального запуска не используются. Для Vision установите extras `backend[dev,vision]` либо используйте [изолированный локальный Vision demo](docs/operations/local-demo-guide.md).

Для временного публичного показа: `pwsh -File .\scripts\windows\start-free-public-demo.ps1`. Quick Tunnel меняет URL и подходит только для демонстрации. Постоянный Agent использует стабильный HTTPS endpoint.

## Тестирование

Нужен доступный локальный PostgreSQL и пользователь с правом `CREATE DATABASE`. Fixture создаёт случайную отдельную БД, применяет migrations и удаляет её после тестов. Перед запуском проверьте локальную connection string. Полная инструкция: [testing strategy](docs/testing/testing-strategy.md).

```powershell
backend/.venv/Scripts/python.exe -m pip install -e 'backend[dev,e2e]'
backend/.venv/Scripts/python.exe -m playwright install chromium

Push-Location backend
.\.venv\Scripts\python.exe -m pytest -q tests/unit tests/integration
$env:ASSETGUARD_RUN_BROWSER_E2E='1'
.\.venv\Scripts\python.exe -m pytest -q tests/e2e
Remove-Item Env:ASSETGUARD_RUN_BROWSER_E2E
Pop-Location

node --check frontend/app.js
git diff --check
```

Без `ASSETGUARD_RUN_BROWSER_E2E=1` browser tests пропускаются. Общий прогон с этим флагом 6 октября: **170 passed in 125.79s**. Он не заменяет реальный fleet test, ручной screen-reader/браузерный аудит и capacity acceptance.

## Windows Agent

Installer `0.1.8` использует неизменённый GLPI Agent как локальный collector, SYSTEM task при загрузке/каждую минуту и защищённую bounded FIFO. Сбор назначается через 300 секунд + jitter 0–60 секунд и задержку scheduler; доставка — максимум три отчёта за цикл, с backoff и XML ACK. Native daemon выключен, чтобы оставался один uploader. Установленные upstream 1.19/1.20 совместимы; новые установки закреплены на 1.20.

Локальный EXE `0.1.8`: **NotSigned**, 2 114 556 bytes, SHA-256 `BCD24D903FDB7C03EACB51E38F3BE653938DD905B0683F360A0BC8B412D3F50F`. Проверен один PC и controlled offline/lost-ACK lab; финальная установка исправленного readiness helper на этом PC ранее была отменена UAC. Полная fleet-приёмка не заявляется.

[Контракт и ограничения](docs/features/agent-continuous-inventory.md), [Windows operations](scripts/windows/README.md), [fleet protocol](docs/operations/agent-fleet-pilot.md), [опубликованный prerelease 0.1.6](https://github.com/temirkhanerbolatovich-coder/AssetGuard/releases/tag/v0.1.6).

## Production и безопасность

Production публикует Caddy на 80/443; API/PostgreSQL находятся во внутренней Docker-сети. `/health/ready` проверяет доступ к БД, но не подтверждает release SHA, актуальность backup или готовность парка. Поле version API/backend пока `0.1.0`; installer имеет отдельную версию. Release определяется SHA и протоколом приёмки.

PostgreSQL backup шифруется AES-256-GCM и проверяется isolated restore из R2. Vision image volume в этот backup не входит. Staging/failover, общая retention policy, MFA/SSO, SAST/container scan/SBOM и внешний pentest остаются открытыми. Лицензия AssetGuard пока не оформлена отдельным `LICENSE`.

Не публикуйте `.env`, Agent secrets, backup passphrase, R2 keys и Telegram token. Не отключайте TLS verification и не меняйте baseline автоматически. Производственная инструкция: [deployment/recovery](docs/operations/production-deployment.md), [security model](docs/security/security-model.md), [observability](docs/operations/observability.md).

## Документация

[Карта документов](docs/README.md) содержит все актуальные руководства, feature contracts и восемь ADR. [Changelog](CHANGELOG.md) сохраняет историю изменений. Исходные требования, spikes и dated reports сохранены с историческими пометками; их измерения не переименованы в результаты сегодняшнего аудита.
