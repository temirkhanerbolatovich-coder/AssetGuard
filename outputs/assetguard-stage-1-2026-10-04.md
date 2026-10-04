# AssetGuard — закрытие первых шагов стабилизации

Дата: 2026-10-04. Исходный Git HEAD: `2b441fb756bd066b234e537357874426cc6f3b05`.

Статус: исправления выполнены и проверены **локально** в рабочем дереве. Commit/push, новый GitHub Actions run и production deployment в эту работу не входили и не выполнены. Новых миграций нет.

Этот статус относится к завершению локального этапа. Следующий этап в тот же день выполнен отдельно: publication, GitHub CI, backup/migration rehearsal и production acceptance зафиксированы в [протоколе выкладки](assetguard-release-2026-10-04.md).

## Что закрыто

| Пункт аудита | Изменение | Подтверждение |
| --- | --- | --- |
| Local environment | PostgreSQL 17 запущена; обычный venv startup исправлен через существующий ASCII junction и editable `.pth`, оригинал сохранён как `.pre-stage1` | Штатный pytest из backend, disposable DB, все 25 migrations до `0025` |
| F-01, Agent scope | Bound endpoint и organization проверяются до endpoint/identifier/snapshot/history changes, включая duplicate и mixed identifiers; first binding входит в commit snapshot; unowned/occupied endpoint не присваивается scoped credential | PostgreSQL negative/positive regressions; FAILED raw может быть обработан правильным Agent с одним change/incident |
| F-02, import tenant | Одна эффективная organization для preview/create/update; отсутствующая колонка означает tenant organization, существующие assets ищутся только в разрешённом scope | Excel и настоящий generic PDF, одинаковый inventory number в разных организациях, mixed-tenant rejection |
| F-03, freshness/monitor | Stale вычисляется по возрасту last_seen без maintenance/записи; monitor очищает fingerprint после recovery, проверяет acceptance и повторяет отказавшую доставку | Tenant-safe counters и Bash contract с подставными API/delivery, isolated state |
| F-04, CI settings | Smoke job получает обязательные database/inventory/admin env settings; Vision detector/model не изменены | Actionlint и offline real-model smoke на текущих исходниках |
| F-06, количественный import | quantity/unit/tracking_mode в Excel/PDF/OCR preview/apply/export, validation целого количества, safe unknown OCR, сохранение учёта после MOVE/WRITE_OFF | Create/update/repeat/export, official statement, unknown OCR, настоящие акты в MVP integration; browser preview |

## Итоговая проверка

- `backend/.venv/Scripts/python.exe -m pytest -q tests/unit tests/integration`: **80 passed**, 39.12 s.
- `ASSETGUARD_RUN_BROWSER_E2E=1` и штатный pytest `tests/e2e`: **2 passed**, 21.74 s.
- Реальная Grounding DINO: **PASS, 23 detections**, существующий CPU image, текущий backend source и demo mounts read-only, model cache read-only, `--network none`. Runtime: torch `2.14.0+cpu`, transformers `5.17.0`; download не проверялся.
- `pip check`: **No broken requirements found**.
- `pip-audit --strict --no-deps --disable-pip`: **No known vulnerabilities found**, manifest 76 установленных внешних packages.
- Gitleaks: **no leaks** в tracked diff и новых исходниках/документах; это проверка изменений, а не новый полный Git-history scan.
- Actionlint: **PASS**.
- JS syntax: **PASS**; Python AST: **93 files PASS**; PowerShell parser: **33 scripts PASS**; Bash syntax: **PASS**.
- Production/free-demo Compose config: **PASS**, безопасные CI env overrides.
- Markdown relative file links и `git diff --check`: **PASS**.

До исправлений начальные PostgreSQL regressions дали 9 failures / 1 pass: подтвердили принятие чужих duplicates и доменные изменения до отказа. Итоговый набор включает новые случаи scope и количественного учёта.

## Документация и решения

Обновлены README, CHANGELOG, current-project-checklist, API/security/data-flow, testing strategy, PDF/OCR и observability. [ADR-006](../docs/decisions/ADR-006-import-accounting-precedence.md) фиксирует приоритет выполненных актов над повторным импортом. [Аудит](assetguard-audit-2026-10-04.md) сохраняет исходный снимок до исправлений.

Учётные поля обеих позиций выполненного MOVE/WRITE_OFF сохраняются; import может обновлять описание. Дробный количественный учёт отклоняется. OCR с неизвестным количеством новой позиции требует уточнённого Excel либо исключения строки. Legacy global bootstrap/JSON shared-secret boundary остаётся и требует отдельной миграции credentials.

## Следующий этап

1. Опубликовать проверенные изменения и получить свежий GitHub application CI, включая scheduled/manual real-model smoke. Локальный PASS не означает зелёный GitHub run.
2. Проверить актуальный server backup, R2 isolated restore и actual schema; провести upgrade/recovery rehearsal `0024 → 0025`.
3. Развернуть exact tested revision и проверить UI hash, routes, schema, health и controlled alert acceptance/получение пользователем.
4. Принять Agent lifecycle/re-enrolment на 3–5 реальных ПК, затем подписанную поставку/update/rollback.

Production SSH/schema, новые server timers/R2 cycles, реальная Telegram-доставка и новый fleet test в этом прогоне не проверялись. Оригинальное ТЗ не изменено.
