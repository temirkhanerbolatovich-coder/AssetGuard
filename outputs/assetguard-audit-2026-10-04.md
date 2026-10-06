# AssetGuard: аудит состояния и следующий план

> **Исторический документ.** Даты, SHA, измерения и исходные требования ниже относятся к описанному этапу. Сверка указателя выполнена 2026-10-06; текущее состояние и оставшаяся работа — в [checklist](../docs/product/current-project-checklist.md) и [аудите](../docs/quality/project-audit-2026-10-06.md).

Дата проверки: **4 октября 2026 года**, Asia/Qyzylorda. Работа выполнена как аудит; исходный код, ТЗ, конфигурация и production не изменялись.

## 1. На каком этапе проект

**Функциональный pilot MVP создан. Текущий этап — исправление обнаруженных ошибок, согласование repository/production и эксплуатационная приёмка. Готовность к нескольким реальным школам не подтверждена.**

Основной поток исходного ТЗ существует: `GLPI inventory → immutable raw evidence → normalized snapshot → explicit baseline → change → incident → human decision → history`.

Проект уже вышел за исходный компьютерный MVP: реализованы реестр школьного имущества, помещения, физические обходы, перемещение/списание, PDF-акты, импорт/экспорт и демонстрационный Vision. Эти возможности не нужно разрабатывать повторно. Сейчас важнее исправить реальные дефекты и проверить существующие сценарии.

### Три разных состояния поставки

| Контур | Что установлено проверкой |
| --- | --- |
| Локальный checkout | `main`, HEAD `2b441fb756bd066b234e537357874426cc6f3b05`; отслеживаемые файлы без изменений до аудита |
| GitHub default branch | Тот же HEAD; 241 файл в полном Git tree; последний application/docs commit от 27.09.2026 |
| Публичный сервер | UI, `/health`, `/health/ready` и `/openapi.json` отвечают HTTP 200; 57 admin operations; re-enrolment routes отсутствуют |
| Публичный frontend | SHA-256 `app.js` совпадает с Git-версией `7a3f7f2`, отличается от HEAD |
| Схема repository | 25 миграций, одна непрерывная цепочка, head `0025_agent_reenrolment` |
| Схема production | В runbook последняя проверка на `0024_physical_asset_operations`; прямое чтение Alembic version сервера в этом аудите не выполнялось |

Совпадение одного публичного файла с `7a3f7f2` подтверждает версию этого файла, но не идентичность всего серверного checkout/container. Отсутствие новых routes отдельно подтверждает, что текущий публичный API не предоставляет repository re-enrolment.

## 2. Что изучено и как интерпретировать проверку

- Инвентаризированы все **241 отслеживаемый файл** локального проекта и GitHub tree. Перечень находится в [инвентаризации файлов](assetguard-file-inventory-2026-10-04.md).
- Сопоставлены исходное ТЗ MVP, Vision requirements, анализ/исследование, актуальный checklist, roadmap, ADR, API/security/deployment/testing документы и старый DOCX передачи работы.
- Разобраны основные HTTP boundaries, источники инвентаризации, normalizer, baseline/diff/incidents/history, tenant/location authorization, импорты, physical workflows, Agent lifecycle, frontend routes и CI/operations scripts.
- Все 90 Python-файлов прошли синтаксический AST-разбор; 33 PowerShell-скрипта — parser check; проверены ссылки всех 56 отслеживаемых Markdown-файлов.
- Прочитаны GitHub Actions jobs/logs для актуального HEAD, сведения о release, открытых PR и защите `main`; выполнены read-only публичные HTTP-проверки.

Это аудит структуры, требований, ключевых путей выполнения и доступных проверок. Он **не является утверждением о построчной ручной проверке каждого файла, испытании всех 66 статических кнопок или выполнении каждого production workflow**. Бинарные установщики проверены по hash/signature; тяжёлые модели, содержимое пользовательских файлов и секреты не выгружались.

## 3. Требования и реализация

| Требование / область | Фактическое состояние | Основание и граница |
| --- | --- | --- |
| Неизменённый GLPI collector, свой backend и PostgreSQL | Реализовано | Native XML adapter и JSON bridge; upstream Agent не форкается |
| Immutable raw payload и idempotency | Реализовано | Inventory service, SHA-256, миграционные triggers; CI workflow |
| Asset отдельно от ManagedEndpoint | Реализовано | Разные модели, явный link; групповой учёт отдельно от Agent |
| Hardware identity, hostname history, конфликты | Реализовано | Normalizer и identity integration tests; реальный fleet acceptance ещё нужен |
| Snapshot completeness, безопасность PARTIAL | Реализовано для поддержанного потока | RAM/STORAGE сравниваются только при COMPLETE; отсутствие категории не создаёт removal |
| Явное принятие baseline | Реализовано | Отдельный admin action, уникальный ACTIVE baseline; ingestion не меняет baseline |
| Diff, evidence, dedup, incident, решения | Реализовано | Основной integration/E2E critical path прошёл в CI |
| Offline означает необходимость проверки | Реализовано как policy | `REQUIRES_VERIFICATION`; обнаружена ошибка передачи этого состояния мониторингу |
| CPU/GPU/board/network/monitor presentation | Реализовано | Normalizer/API/UI; детектор material changes сейчас ориентирован на RAM/STORAGE и endpoint identity |
| Реестр, индивидуальные/групповые позиции | Реализовано вручную | Категория, tracking mode, количество и unit; перенос этих полей через импорт неполон |
| Корпус → этаж → кабинет, права сотрудника | Реализовано | API и location grants; отдельного organization create/rename workflow нет |
| Физический обход, расхождения, решения | Реализовано | Каждая текущая позиция отмечается; actor/время/история; integration/E2E |
| Перемещение/списание и PDF-акт | Реализовано | Включая частичные операции групповых позиций |
| Excel/PDF/OCR | Рабочий поддержанный путь, есть дефекты | Preview/apply, исключение строк; обнаружены tenant fallback и потеря структурированного количества |
| Пользователи, сессии, роли, admin matrix | Реализована foundation | 60 операций в HEAD; обнаруженные ingestion/import ошибки показывают неполноту защиты всех boundaries |
| Per-Agent credentials, revoke | Реализовано | Имеется ошибка проверки принадлежности при приёме inventory |
| Approved re-enrolment и installer version | Реализовано в repository | `0025`; публичный сервер эти routes пока не предоставляет |
| Windows installer | Пилотная поставка | `0.1.6` опубликован как prerelease; `0.1.7` локальный candidate; оба EXE NotSigned |
| Vision photo → detection → baseline → WARNING | Локальный demo slice | Существующие тесты/артефакты; последний real-model CI smoke не прошёл конфигурацию |
| Production Vision | Не подготовлен | Oracle Free overlay отключает ML runtime; нет object storage, image backup/retention и evaluation dataset |
| HTTPS production | Сейчас доступен | HTTP 200 UI и health/readiness; это не проверка всех функций |
| R2 backup/restore и Telegram | Инструменты и историческая приёмка есть | Последняя запись от 27.09; текущие server jobs/R2 objects и получение Telegram пользователем не перепроверялись |
| Multi-school readiness | Не подтверждена | Дефекты tenant boundaries, fleet/governance/lifecycle и приёмка двух организаций остаются открытыми |

Интеграции 1С/helpdesk/AD, мобильный/PWA-обход и RTSP были исключены из исходного MVP либо относятся к последующим этапам. Их отсутствие не означает, что исходный компьютерный MVP не создан. Аналогично GLPI API sidecar был fallback: после подтверждения прямого транспорта создавать его ради соответствия старому исследованию не требуется.

## 4. Обнаруженные проблемы

### F-01 — P0: принадлежность Agent проверяется после записи; duplicate обходит проверку

Код: [glpi_agent.py](../backend/src/assetguard/interfaces/http/glpi_agent.py), строки 83–101; [normalizer.py](../backend/src/assetguard/modules/snapshots/normalizer.py), глобальный поиск identifiers и commit на строке 224.

В non-duplicate ветке normalizer уже сохраняет изменения до сравнения credential endpoint. При первом bind существующий endpoint может получить организацию credential без проверки его текущего владельца. В duplicate ветке статус/last-seen endpoint обновляются без проверки соответствия credential этому endpoint.

В отдельном Python-процессе вызван **настоящий HTTP handler**, а persistence/normalizer подменены локальными fake objects; публичный сервер не использовался:

- duplicate для foreign endpoint с credential другого endpoint: ответ `200`, один commit, статус foreign endpoint стал `ONLINE`;
- первый bind credential организации A к endpoint организации B: ответ `200`, один commit, организация endpoint изменилась на A.

Это подтверждает поведение обработчика при соответствующих результатах lookup. Полный end-to-end exploit/regression на PostgreSQL не выполнялся. Глобальный lookup и порядок commit независимо видны в текущем коде.

**Закрытие:** проверять credential/tenant/endpoint до нормализации доменных данных; duplicate применять только в разрешённом scope; первая привязка не должна переносить endpoint между организациями. Raw evidence можно сохранять по принятой policy, но rejected ingest не должен менять чужой endpoint/snapshot/history/credential. Нужны PostgreSQL negative tests для нового отчёта, duplicate, первого bind и rejected credential mismatch.

### F-02 — P0: импорт без organization записывает в Default Organization

Код: [admin_assets.py](../backend/src/assetguard/interfaces/http/admin_assets.py), `_import_assets`, строки 458–489.

Validation трактует пустую organization как организацию principal. Preview/apply затем используют другую подстановку — `Default Organization`. Именованный administrator школы B может пройти проверку и создать либо обновить запись в Default Organization. Поиск existing assets также выполнен глобально.

Настоящий `_import_assets` вызван в отдельном процессе с fake Session и двумя локальными организациями. Результат: `applied=true`, один commit, созданный asset оказался вне организации principal. Рабочая PostgreSQL не изменялась.

**Закрытие:** единое разрешение целевой organization для preview и apply; named admin всегда ограничен собственной организацией; existing lookup фильтруется по разрешённому scope. Тестировать пустую/явную/чужую organization, совпадающие inventory numbers в разных schools, create/update и mixed rows через Excel и PDF paths.

### F-03 — P1: монитор не считает REQUIRES_VERIFICATION

Код: [endpoints/service.py](../backend/src/assetguard/modules/endpoints/service.py), строка 17; [health.py](../backend/src/assetguard/interfaces/http/health.py), строки 98–99; [server-monitor.sh](../scripts/linux/assetguard-server-monitor.sh), строки 90–98.

Last-seen policy переводит endpoint в `REQUIRES_VERIFICATION`. Operations API считает `OFFLINE` и `STALE`; Linux monitor суммирует только эти два счётчика. В локальном вызове настоящего `operations_status` с fake query result для одного `REQUIRES_VERIFICATION` endpoint сумма offline/stale оказалась **0**.

**Закрытие:** согласовать модель статусов и freshness policy, проверить отсутствие свежего отчёта даже без ручного maintenance call, затем проверить обнаружение условия, контролируемое получение уведомления, дедупликацию и восстановление. Старая проверка `--test-alert` сама по себе не доказывает обнаружение просроченного Agent.

### F-04 — P1: последний CI красный из-за окружения Vision smoke

[CI run 36374203808](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/36374203808), 28.09.2026, тот же HEAD `2b441fb`:

- `test`: success; **50 passed** unit/integration и **2 passed** browser E2E;
- `Secret scan`: success;
- `Grounding DINO real-model smoke`: failure — `RuntimeError: ASSETGUARD_DATABASE_URL must be configured.`

Smoke job задаёт HF_HOME, но вызывает detector с общим `get_settings`, которому нужны обязательные application variables. На данном запуске проверка упала до inference: это не доказательство поломки модели. Успешные Dependabot update jobs от 01.10 не заменяют этот application CI.

**Закрытие:** исправить environment smoke job без изменения Vision inference, выполнить новый полный CI с real-model smoke и отдельно отразить результат. Новые реальные secrets для smoke не нужны.

### F-05 — P1: production отстаёт от repository

Публичный `app.js` совпадает с `7a3f7f2`; routes re-enrolment отсутствуют; repository содержит `0025` и новые frontend/admin actions. Поэтому `0.1.7` нельзя принимать как готовый production lifecycle на текущем сервере.

**Закрытие:** после F-01/F-02/F-04 подготовить exact release, свежий backup + isolated restore, upgrade rehearsal и API/image rollback; развернуть проверенный commit; проверить actual migration revision, routes, assets и полный lifecycle. Downgrade `0025` меняет привязки revoked credentials, поэтому откат схемы требует отдельной проверки, а не только старого Docker image.

### F-06 — P1: импорт группового количества не завершён

`_import_row_values` не переносит `quantity`, `unit`, `tracking_mode`. `_government_inventory_rows` кладёт количество/единицу в notes. `_import_assets` не назначает эти структурированные поля; default модели — `quantity=1`, `tracking_mode=INDIVIDUAL`.

Документ PDF/OCR частично признаёт хранение количества в примечании. Название unit test про grouped assets и общий checklist создают более широкое впечатление, чем реальное поведение импорта.

**Закрытие:** переносить и валидировать количество/единицу/режим учёта в preview и apply; определить обработку дробных бухгалтерских количеств; проверять create/update, повторный импорт и сохранение остатков после физической операции. Оператор не должен считать 12 парт одной индивидуальной единицей из-за формата импорта.

### F-07 — открытые release/security/product gates

- Оба проверенных installer `0.1.6`/`0.1.7` имеют `NotSigned`; managed update/rollback и 3–5 полных fleet cycles не приняты.
- Legacy shared credentials и глобальный bootstrap path остаются включены; named-user/Agent migration нужно завершить перед расширением.
- Нет отдельной формы/API create/rename organization. Bootstrap import может создавать organizations неявно, что не заменяет управляемое подключение школы. Tenant-scoped ADMIN уже существует; нужно определить platform/tenant полномочия и onboarding, а не создавать вторую роль ради названия.
- Нет утверждённой retention/deletion policy; PostgreSQL backup не включает Vision images.
- Нет staging, проверенного release/rollback на текущей миграции, нагрузочной приёмки, MFA/SSO и единого admin audit.
- `main` не защищён, rulesets пусты; открыты Dependabot PR [#7](https://github.com/temirkhanerbolatovich-coder/AssetGuard/pull/7) и [#8](https://github.com/temirkhanerbolatovich-coder/AssetGuard/pull/8). В этом аудите они не сливались.
- LICENSE отсутствует; решение о лицензировании ещё не зафиксировано.
- API/backend version остаётся `0.1.0`, хотя Agent release — `0.1.6`. Нужна понятная запись application version, deployed commit и installer version.

## 5. Документация и старый контекст

Рабочая карта — [docs/README.md](../docs/README.md), основной учёт — [current checklist](../docs/product/current-project-checklist.md), архитектура — актуальные architecture documents и ADR. Исходное ТЗ хранит обязательные инварианты; его не следует переписывать под найденные ошибки.

Обнаружены несогласованности:

1. Старый DOCX передачи работы сообщает 27 backend tests, незавершённый server Telegram и необходимость реализовать Incident Detail/Device tabs. Эти этапы уже продвинулись: текущий CI содержит 50 backend tests и 2 E2E; карточки/вкладки существуют, server tooling и историческая приёмка записаны.
2. Checklist в сводке говорит о 60 operations, но один подпункт этапа 2 всё ещё содержит 57. Для HEAD верно 60; для публичного сервера сейчас наблюдается 57.
3. UX document оставляет задачу заменить browser prompt/confirm, хотя в текущем app.js таких вызовов нет.
4. Security baseline говорит о едином лимите 10 MB на API/proxy, а inventory boundary использует 2 MiB по умолчанию; proxy/Vision limits описываются отдельно.
5. Data ownership document содержит старые формулировки о будущей реализации схемы и ранней миграции, хотя schema уже имеет 25 migrations.
6. Architecture/module-boundary тексты строже фактической реализации: modules используют общие ORM models и прямые запросы друг к другу; нет отдельной queue/outbox, а Vision inference работает внутри API. Старый research proposal нельзя считать описанием установленной архитектуры.
7. Формулировка «CI работает» требует поправки по F-04, а «tenant isolation готова» — по F-01/F-02.

Обновление канонических документов предлагается вместе с будущими исправлениями. В этом аудите сохранён отдельный отчёт; исходное ТЗ и существующие документы не переписывались.

## 6. Реально выполненные проверки

| Проверка | Результат |
| --- | --- |
| Git status / HEAD / GitHub default branch / recursive tree | HEAD совпадает; 241 tracked file; Git tree не усечён |
| Python AST | 90 файлов; синтаксических ошибок нет |
| PowerShell Parser | 33 скрипта; ошибок нет |
| Markdown relative links | 56 файлов; broken relative links не найдены |
| `node --check frontend/app.js` | PASS |
| `git diff --check` до создания отчёта | PASS |
| Миграционная цепочка, статически | 25 миграций, один head, отсутствующих predecessors нет |
| Локальный pytest collection | 50 unit/integration cases собраны; это не выполнение 50 тестов |
| Локальные независимые unit checks | **28 passed, 1 deselected**; запущены без общей DB fixture (`--confcutdir=tests/unit`), DB readiness исключён |
| Полный штатный локальный pytest | Не завершён: PostgreSQL `127.0.0.1:5433` недоступна, Docker daemon не запущен; ожидание подключения остановлено |
| Python environment | Обычный venv startup ломается на `.pth`/cp1251; использован существующий подход Python `-S` + explicit source/site-packages |
| Локальный browser E2E / real inference / PostgreSQL upgrade | В этом аудите не запускались успешно |
| Исторические CI logs актуального HEAD, 28.09 | 50 backend + 2 E2E passed; dependency audit и secret scan success; Vision smoke failure |
| Handler reproductions F-01/F-02/F-03 | Поведение настоящих функций проверено с fake persistence в отдельных процессах; не PostgreSQL integration |
| Публичный HTTPS | UI/health/readiness/OpenAPI HTTP 200; frontend hash и route surface сопоставлены |
| Installer signatures | `0.1.6` и `0.1.7`: NotSigned; hashes соответствуют локальным `.sha256` |
| Frontend structural scan | 281 статический id без дублей; 66 статических buttons; обнаруженные динамические id присутствуют в JS templates; prompt/confirm нет |
| SSH/systemd/R2/fleet/user acceptance | Текущая серверная приёмка и реальный парк в этом аудите не проверялись |

Локальная команда для 28 независимых проверок использовала Python 3.12 с `-S`, явные `C:/AssetGuardDev/backend-venv/Lib/site-packages` и `src`, затем pytest для route contract, Agent version, schema, normalizer, raw hash, privacy fixture, capacity, health без DB readiness и cross-platform backup crypto. Это диагностический запуск для данного Windows environment; штатный полный прогон требует PostgreSQL и обычной disposable fixture.

Hashes локальных installer:

- `0.1.6`: `813FB8AE93F1BB96963A3BE4B9466B587A37ACDECB86DBB4E322004255907179`.
- `0.1.7`: `40AC4EC6D484815AA81A4EC3046686B9AF68C6D4E6E6D5FE4CDC6FA7EB85D6F9`.

## 7. Предлагаемый порядок работы

### Этап 1. Исправить подтверждённые дефекты и восстановить проверяемый baseline

**Последующее выполнение 2026-10-04:** по отдельному запросу «гоу закроем первые шаги» локально исправлены F-01/F-02/F-03/F-04/F-06, восстановлены PostgreSQL/venv и выполнены 80 backend + 2 browser tests, offline real-model smoke. Исходные findings выше оставлены как снимок до исправлений. Детали и оставшиеся GitHub/server gates — [отчёт первого этапа](assetguard-stage-1-2026-10-04.md).

1. Поднять изолированный local/staging PostgreSQL, восстановить воспроизводимый test startup на Windows.
2. Добавить и выполнить PostgreSQL regression tests для F-01/F-02, исправить credential/tenant boundaries до доменных записей.
3. Исправить freshness counters/monitor F-03; проверить состояние, delivery/dedup/recovery в разрешённом контролируемом окружении.
4. Исправить smoke job configuration F-04 без изменения Vision detector/model/storage.
5. Завершить импорт количества/единицы/режима учёта F-06 и защитить повторный импорт/остатки тестами.
6. Выполнить весь unit/integration/E2E suite, security/config checks и scheduled/manual real-model CI; синхронизировать checklist/docs с результатами.

**Выход:** оба tenant bypass закрыты автоматическими негативными проверками, импорты не искажают учёт, monitor обнаруживает просроченный Agent, полный CI зелёный.

### Этап 2. Согласовать сервер с проверенным release

1. Зафиксировать application version, commit, schema и installer compatibility.
2. Проверить свежий production encrypted backup, R2 download и isolated restore; получить текущую revision и состояние jobs.
3. В staging провести upgrade `0024 → 0025`, re-enrolment и rollback/recovery rehearsal.
4. Сохранить прежний API image и развернуть exact tested commit; проверить UI hashes, routes, actual migration revision и health.
5. Пройти реальный сквозной сценарий подключения/отзыва/восстановления Agent на контролируемом ПК.

**Выход:** известно, что именно работает на сервере; новые routes доступны; rollback и восстановление проверены. Deployment выполняется отдельной согласованной работой после аудита.

### Этап 3. Принять парк Agent и безопасную поставку

1. Установить candidate на 3–5 разных Windows-PC с уникальными credentials.
2. Для каждого выполнить INITIAL, AFTER_REBOOT, OFFLINE, NETWORK_RESTORED, SERVICE_RECOVERED, REENROLLED и HARDWARE_CHANGED; проверить реальные новые inventory timestamps на сервере.
3. Отдельно проверить чистую переустановку Windows и несовпадающие/клонированные identifiers.
4. Подтвердить сохранение endpoint/asset/history, отзыв старого ключа и ровно один объяснимый incident.
5. Подписать installer, подготовить versioned update/rollback и испытать обновление/откат. Контролируемая ручная передача unsigned candidate допускается только в существующих рамках внутреннего пилота.

**Выход:** 3–5 полных протоколов и воспроизводимый lifecycle; для расширения — подписанная поставка и проверенный rollback.

### Этап 4. Закрыть управление данными и эксплуатацию

Подготовку policy начать параллельно с этапом 1; допуск реальных школьных данных зависит от её согласования.

1. Утвердить data inventory, владельцев/доступ, место хранения и retention/export/delete отдельно для inventory/history/images.
2. Завершить переход на named users/per-Agent credentials и отключить либо строго ограничить bootstrap/legacy paths.
3. Ввести единый audit users/grants/credentials/imports/settings, staging/release runbook и MFA/SSO по принятому scope.
4. Проверить автоматические backup/restore cycles и наблюдаемость; если Vision images входят в пилот, отдельно принять image backup/restore.
5. Настроить protection `main`, review dependency PR, определить license и дополнительные supply-chain checks.

**Выход:** approved policy и доступы, актуальные recovery evidence, управляемые releases; нет зависимости от общего ключа для обычной работы школы.

### Этап 5. Принять реальный школьный workflow и несколько организаций

1. Добавить понятный organization onboarding/create/rename и platform/tenant access model.
2. Пройти на двух организациях UI/API сценарии пользователей, устройств, импортов, exports, Vision images/history и grants; включить найденные bypass paths.
3. С сотрудниками школы проверить импорт → распределение по кабинетам → обход → incident → решение → перемещение/списание → PDF/Excel.
4. Исправить только выявленные функциональные/UX проблемы; затем по потребности добавить сводные отчёты, mapping wizard, QR кабинета/mobile обход.
5. Выполнить нагрузочные/длительные проверки на согласованное число устройств и определить deployment limits.

**Выход:** сотрудники проходят основные действия без работы разработчика с БД; одна школа не читает и не меняет другую; нагрузка и восстановление находятся в проверенных границах.

### Этап 6. Отдельный production Vision и дальнейшие интеграции

Существующий запрет на изменение Vision логики сохраняется для текущего этапа; здесь перечислен будущий отдельный scope.

1. Evaluation dataset и измеренные accuracy/latency по выбранным условиям.
2. Выбор inference infrastructure, object storage, access/retention/image backup.
3. Human confirmation и quality gates; после этого multi-frame/RTSP и mapping detections к активам.
4. 1С/helpdesk/AD integrations — после подтверждённой потребности и контрактов.

**Выход:** измеренная пригодность Vision для целевого сценария; `WARNING` остаётся сигналом проверки человеком.

## 8. Ближайшая конкретная работа

Начать с **регрессий и исправления Agent ingress + tenant fallback импорта**. Затем закрыть monitor/import accounting и CI, провести контролируемый release на сервер и принять lifecycle на 3–5 ПК. Политика данных готовится параллельно. Такой порядок следует текущему коду и найденным сбоям; старые планы реализовать уже готовые Incident Detail/Device tabs повторять не нужно.
