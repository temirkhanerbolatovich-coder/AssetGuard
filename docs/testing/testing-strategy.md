# Стратегия тестирования

## Цель

Тесты защищают основной поток `inventory → evidence → snapshot → baseline → incident → decision → history`, tenant/location isolation, authentication, физический учёт, импорт документов и Vision workflow. Проверяется поведение через публичные функции и HTTP API, а не внутренняя структура реализации.

## Уровни

| Уровень | Что проверяется | Расположение |
| --- | --- | --- |
| Unit | Schema, normalization, raw evidence, health, route contract, PDF import, privacy fixture и backup crypto | `backend/tests/unit/` |
| Integration | PostgreSQL migrations, auth lifecycle, identity, tenant/location scope, GLPI transport, MVP и Vision workflows | `backend/tests/integration/` |
| Browser E2E | Критические сценарии dashboard через Chromium | `backend/tests/e2e/` |
| Real-model smoke | Загрузка Grounding DINO и обработка demo frame | `backend/scripts/vision_real_model_smoke.py` |
| Static/config checks | JavaScript, PowerShell, shell, Python scripts и Compose config | `.github/workflows/ci.yml` |
| Security checks | Gitleaks, `pip check`, `pip-audit` | `.github/workflows/ci.yml` |

В текущем наборе 80 unit/integration и 2 browser E2E tests. Число является снимком состояния репозитория на 2026-10-04 и должно обновляться вместе с изменением набора.

## Тестовое окружение

Backend требует Python 3.12 и доступный PostgreSQL. Session fixture:

1. подключается к server из `ASSETGUARD_DATABASE_URL`;
2. создаёт отдельную базу со случайным именем;
3. применяет Alembic migrations до `head`;
4. перед каждым тестом очищает таблицы и состояние rate limiter;
5. после session завершает соединения и удаляет тестовую базу.

Это защищает рабочую базу при условии, что connection string указывает на PostgreSQL instance, где test user имеет право создавать и удалять базы. Никогда не используйте production credentials для локального запуска тестов.

## Локальный запуск

Из корня репозитория:

```powershell
pwsh -File .\scripts\windows\new-local-env.ps1
docker compose --env-file .env -f infra/containers/docker-compose.yml up -d postgres
py -3.12 -m venv backend/.venv
backend/.venv/Scripts/python.exe -m pip install -e 'backend[dev,e2e]'
backend/.venv/Scripts/python.exe -m playwright install chromium
```

Unit и integration:

```powershell
Push-Location backend
.\.venv\Scripts\python.exe -m pytest -q tests/unit tests/integration
Pop-Location
```

Browser E2E запускаются явно:

```powershell
$env:ASSETGUARD_RUN_BROWSER_E2E = '1'
Push-Location backend
.\.venv\Scripts\python.exe -m pytest -q tests/e2e
Pop-Location
Remove-Item Env:ASSETGUARD_RUN_BROWSER_E2E
```

Backup crypto test использует PowerShell 7 (`pwsh`) для проверки совместимости Windows- и Python-реализаций.

Linux monitor contract использует Bash и локальные command doubles с отдельным `--state-dir`, без реальных network/Telegram/systemd/Compose действий. На Windows используется Git Bash; отсутствие Bash явно пропускает этот тест.

Если Python 3.12 завершает startup с `UnicodeDecodeError` в `site.addpackage`/`cp1251`, проверьте editable `.pth`: UTF-8 путь с кириллицей может не читаться Windows locale decoder. Для текущего checkout подтверждён ASCII junction `C:\AssetGuardWorkspace → backend`; editable `.pth` внешнего venv указывает на `C:\AssetGuardWorkspace\src`. Исходный `.pth` сохранён рядом как `.pre-stage1`. После этой локальной коррекции штатные команды выше выполняются без `-S`. Для нового checkout предпочтителен ASCII путь и собственный venv; не переносите абсолютный junction на другой проект.

## CI

На push в `main` и `codex/**`, а также на pull request CI:

1. сканирует всю Git history на secrets;
2. запускает PostgreSQL 17;
3. устанавливает backend с `dev,e2e` dependencies;
4. выполняет dependency и vulnerability checks;
5. запускает unit/integration и browser E2E;
6. проверяет JavaScript и синтаксис Windows/Linux scripts;
7. валидирует production и free-demo Compose.

Grounding DINO real-model smoke выполняется отдельно по расписанию и вручную, потому что требует тяжёлых dependencies и model download.

Smoke job задаёт обязательные `ASSETGUARD_DATABASE_URL`, `ASSETGUARD_INVENTORY_SHARED_SECRET` и `ASSETGUARD_ADMIN_SHARED_SECRET`: detector читает общие settings даже без подключения к БД. Локальная проверка 2026-10-04 прошла на текущем коде в готовом CPU image (`torch 2.14.0+cpu`, `transformers 5.17.0`), offline/read-only cache: 23 detections. Дополнительно [manual GitHub run 37223446315](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37223446315) на application commit `93ff8ed` завершился success, подтвердив настоящий model download/inference и 23 detections; 80 backend tests и 2 browser E2E также прошли. Это runtime smoke, а не accuracy benchmark.

## Требования к изменениям

- Bug fix должен получить regression test, если сценарий воспроизводим автоматически.
- Изменение migration проверяется на чистой базе и, при затрагивании существующих данных, отдельным upgrade-сценарием.
- Новая роль или route требует positive и negative authorization cases.
- Новый ingestion format требует fixtures для валидного, некорректного, повторного и частичного payload.
- Изменение frontend workflow требует E2E только для критичного пользовательского пути; детали отображения лучше проверять на более низком уровне.
- Изменение Vision detector не считается проверенным только на mock: нужен scheduled/manual real-model smoke.

## Подтверждённые пробелы

- Нет нагрузочных и длительных soak tests.
- R2 restore rehearsal реализован как эксплуатационный скрипт: Windows Task Scheduler и постоянный Linux server прошли 2026-09-27. Server rehearsal вернул revision `0024_physical_asset_operations`, `assets=211`, `endpoints=1`. Monitor test mode подтвердил Telegram acceptance и дедупликацию без остановки production.
- Agent re-enrolment integration tests применяют миграцию `0025`, проверяют отсутствие plaintext claim token, tenant isolation, expiry, approve/reject, отзыв прежнего credential и сохранение endpoint.
- Native Agent regression tests проверяют bound mismatch, foreign/unowned organization, mixed identifiers, duplicate, existing active credential и повторную доставку FAILED raw правильным Agent с одним change/incident.
- Import tests проверяют Excel и настоящий generic PDF, tenant preview/create/update, mixed-tenant rejection, целые/дробные количества, official statement, OCR unknown count, повторный импорт/экспорт и остатки после настоящих MOVE/WRITE_OFF.
- Freshness проверяется на старых ONLINE/REQUIRES_VERIFICATION с сохранением tenant filters и отсутствием изменений БД; monitor contract — stale/acceptance/dedup/recovery/recurrence/refusal/retry/malformed metrics.
- Real-model smoke проверяет работоспособность pipeline, но не точность модели на репрезентативном датасете.
- Upgrade/recovery `0024 → 0025 → 0024 → 0025` прошёл 2026-10-04 на свежей копии production из R2: все прежние таблицы сохранили counts/fingerprints после upgrade, прежний API запустился после downgrade, новый API — после re-upgrade. Production readiness/UI hashes/schema/auth и настоящий Telegram acceptance/dedup прошли; [протокол](../../outputs/assetguard-release-2026-10-04.md).
- Реальный fleet GLPI Agent и production failover остаются ручными проверками. Репетиция downgrade на pre-release копии не доказывает сохранность новых re-enrolment requests при позднем откате.

Эти пробелы учтены в [technical debt](../technical-debt.md).
