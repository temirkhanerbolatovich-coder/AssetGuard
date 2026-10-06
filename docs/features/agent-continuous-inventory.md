# Непрерывная аппаратная инвентаризация Agent 0.1.8

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Agent сохраняет аппаратные отчёты на диске независимо от доступности сервера. После восстановления связи отправляет их последовательно и удаляет только после HTTP 200 с XML `<REPLY><RESPONSE>SEND</RESPONSE>`. Повторная попытка использует исходные байты: серверная SHA-256 дедупликация предотвращает повторную обработку одного отчёта.

## Сбор и доставка

- Windows Task `AssetGuard inventory delivery` работает от SYSTEM при загрузке и каждую минуту, с задержкой 0–30 секунд. Одновременные экземпляры запрещены; дополнительно очередь защищает файловая блокировка.
- По умолчанию следующий сбор назначается через 300 секунд плюс случайные 0–60 секунд. Фактический старт зависит от минутного задания, его задержки, длительности предыдущего сбора и состояния Windows. Спящий или выключенный компьютер не собирает данные.
- Неизменённый GLPI Agent 1.19/1.20 запускается как локальный collector с отдельным аппаратным профилем без server target и credentials. Его сетевой daemon отключается после регистрации задания, чтобы работал один uploader.
- XML сначала сохраняется атомарно с GUID, SHA-256 и временем сбора; полные `.tmp` восстанавливаются после прерывания. Успешно сохранённые отчёты переживают перезапуск рабочего процесса.
- Первичная отправка и восстановление сетевого адаптера получают задержку 0–60 секунд. За цикл отправляется максимум три отчёта с паузами 5–15 секунд. Ошибки сети/5xx/невалидный ответ вызывают случайный backoff с верхней границей 60, 120, 240, затем 300 секунд. `Retry-After` учитывается до 3600 секунд.
- Наличие активного адаптера не доказывает наличие интернета. Если адаптер остаётся активным, восстановление доступа обнаруживается очередной HTTP-попыткой после backoff.
- При 401/403/409 отчёт остаётся в очереди, повтор не раньше 300 секунд. Отзыв ключа не превращается в потерю истории. 400/413/415/422 и повреждённые отчёты сохраняются в `rejected` для диагностики.
- Ограничение очереди: 256 MiB и 10 000 файлов по умолчанию, включая `rejected`. При заполнении сохраняются прежние отчёты, новые сборы приостанавливаются с `QUEUE_FULL`. Перед сбором требуется 32 MiB свободного места. Это ограниченная очередь, а не гарантия бесконечного хранения offline.

## Установка и обновление

Собрать EXE: `scripts/windows/build-agent-installer.ps1`. Installer 0.1.8 имеет три режима: новое подключение, approved re-enrolment после переустановки Windows и обновление с сохранением подключения. Обновление не требует нового ключа и не инициирует re-enrolment. Оно переиспользует защищённые локальные credentials, сохраняет очередь и endpoint, проверяемый сервером по hardware identity.

Для обновления уже подключённого PC из повышенного PowerShell (без параметра используется сохранённый адрес):

```powershell
.\scripts\windows\update-assetguard-agent.ps1 `
  -GatewayUri 'https://assetguard-temirkhan.duckdns.org/glpi-agent'
```

Настроить частоту при новой установке или переустановке конфигурации:

```powershell
$secret = Read-Host 'Inventory secret' -AsSecureString
.\scripts\windows\install-assetguard-agent-service.ps1 `
  -GatewayUri 'https://<host>/glpi-agent' -AgentUsername '<device-login>' `
  -InventorySecret $secret -CollectionIntervalMinutes 5 `
  -CollectionJitterSeconds 60 -MaxQueueMegabytes 256 -RunInventoryNow
```

Права администратора обязательны для задания SYSTEM, ACL и изменения службы. Установщик не обходит UAC. Отдельные файлы/каталоги runtime и их владелец ограничены SYSTEM/Administrators. Пароль остаётся в защищённом `HKLM\SOFTWARE\GLPI-Agent`; его нет в Task arguments, `policy.json`, JSONL или EXE. HTTPS обязателен, redirects запрещены, ответ ограничен 64 KiB, XML DTD запрещён. Collector timeout — 120 секунд, HTTP timeout — 30 секунд.

После обновления дождаться первой доставки и выполнить от администратора:

```powershell
.\scripts\windows\test-assetguard-agent-readiness.ps1 `
  -ExpectedInstallerVersion '0.1.8' -ExpectedAgentVersion '1.19' -Phase INITIAL
```

Для свежей установки upstream 1.20 указать `-ExpectedAgentVersion '1.20'`. Скрипт читает только metadata реестра и проверяет существование password value, не извлекает пароль. Старые installer можно проверить с явной ожидаемой версией. Удаление прекращает задание, удаляет managed credentials и оставляет защищённую очередь/диагностику; не удаляйте её без решения владельца данных. После ошибки обновления проверяйте состояние задания и повторяйте установку: автоматический rollback не реализован.

## Диагностика

Все пути ниже находятся в `%ProgramData%\AssetGuard\Agent`:

| Путь | Назначение |
| --- | --- |
| `policy.json` | Частота, jitter, quota, путь upstream; без credentials |
| `state.json` | Следующие сроки в Unix seconds и retry counter |
| `pending/*.json` | Неотправленные XML в base64, GUID, SHA-256, время сбора |
| `rejected/` | Повреждённые или отклонённые отчёты; сохраняются до ручного разбора |
| `runtime.jsonl` | Время, фиксированный код события и GUID; ротация 5 MiB плюс одна копия |
| `collector/collector.log` | Закрытая диагностика upstream collector; не публиковать без проверки |
| `runtime/` | Защищённые скрипты и аппаратный профиль задания SYSTEM |

Коды `COLLECTED`, `DELIVERED`, `NETWORK_UNAVAILABLE`, `NETWORK_RESTORED`, `DELIVERY_RETRY`, `AUTH_REJECTED`, `SERVER_REJECTED`, `COLLECTION_FAILED`, `QUEUE_FULL`, `QUEUE_CORRUPT`, `QUEUE_RECOVERED`, `STATE_RECOVERED` позволяют отличать отсутствие сбора, недоступность сервера и отказ авторизации. Для `COLLECTION_FAILED` дополнительно проверить закрытый collector log и свободное место. Runtime XML содержит hardware identifiers: очередь не является публичным журналом.

## Серверная совместимость и ограничения

`ASSETGUARD_GLPI_PROLOG_INTERVAL_SECONDS=360` задаёт штатным старым Agent PROLOG в дробных часах вместо прежних 24 часов. Допустимо 60–86400 секунд; production/free-demo Compose передаёт настройку. Старый Agent увидит её только при следующем контакте: уже сохранённый суточный deadline сервер удалённо не отменяет. Укороченный PROLOG сам по себе не обеспечивает накопление offline отчётов; для этого нужен 0.1.8.

В immutable XML сохраняется `ASSETGUARD_CAPTURED_AT`, но текущая серверная модель/панель продолжает датировать snapshot временем приёма. Точная offline timeline ещё не отображается по времени сбора. FIFO сохраняет порядок изменений. Доставка — at least once с дедупликацией, не exactly once. Повтор существующего отчёта после потери ACK проверен тестами transport и queue.

Версия installer читается из штатного native `CONTENT/ACCOUNTINFO` с `KEYNAME=TAG` или bridge `CONTENT/TAG`; ранее принятые immutable отчёты не переписываются. Readiness проверяет SYSTEM по SID `S-1-5-18`, включая локализованное имя Windows.

Частые отчёты увеличивают объём БД. До массового развёртывания нужны замеры на реальном парке и политика retention. Текущий серверный лимит ingest по IP и 429 сохраняются; несколько PC за одним NAT могут попасть под него даже с jitter. Backoff снижает повторную нагрузку, но не заменяет capacity planning. Публичный installer 0.1.6 не обновляется автоматически; 0.1.8 пока кандидат без code signing и без полной fleet-приёмки 3–5 PC.

## Проверка

`backend/tests/unit/test_agent_runtime.py` исполняет поставляемый PowerShell runtime с реальными временными файлами и контролируемым HTTP сервером. Покрыты offline FIFO, ограничение batch, lost ACK, jitter/Retry-After, restart recovery/lock, quota/corruption, revoke, HTML/redirect/oversized response вместо ACK. `test_agent_schedule.py` и native transport integration проверяют настройку и обе upstream версии. На Windows дополнительно запускать эти runtime tests с `ASSETGUARD_AGENT_TEST_POWERSHELL=C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe`.

Реальная приёмка reboot, SYSTEM ACL/task, длительного отключения сети и нескольких PC описана в [fleet test](../operations/agent-fleet-pilot.md). Архитектурное решение: [ADR-008](../decisions/ADR-008-agent-durable-delivery.md).
