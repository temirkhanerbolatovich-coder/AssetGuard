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

В текущем наборе 30 unit/integration и 2 browser E2E tests. Число является снимком состояния репозитория и должно обновляться вместе с изменением набора.

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

## Требования к изменениям

- Bug fix должен получить regression test, если сценарий воспроизводим автоматически.
- Изменение migration проверяется на чистой базе и, при затрагивании существующих данных, отдельным upgrade-сценарием.
- Новая роль или route требует positive и negative authorization cases.
- Новый ingestion format требует fixtures для валидного, некорректного, повторного и частичного payload.
- Изменение frontend workflow требует E2E только для критичного пользовательского пути; детали отображения лучше проверять на более низком уровне.
- Изменение Vision detector не считается проверенным только на mock: нужен scheduled/manual real-model smoke.

## Подтверждённые пробелы

- Нет нагрузочных и длительных soak tests.
- Нет полного автоматизированного allow/deny matrix для всех admin routes.
- Нет автоматического production restore test из R2.
- Real-model smoke проверяет работоспособность pipeline, но не точность модели на репрезентативном датасете.
- Реальный fleet GLPI Agent и production failover остаются ручными проверками.

Эти пробелы учтены в [technical debt](../technical-debt.md).
