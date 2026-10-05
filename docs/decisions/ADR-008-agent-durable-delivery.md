# ADR-008: Независимый локальный сбор и ограниченная очередь Windows Agent

Status: Accepted  
Date: 2026-10-05

## Context

Agent выдавал первый inventory, затем исчезал из активного обмена. Gateway возвращал `PROLOG_FREQ=24` в часах. Установочный `delaytime=60` задавал начальный контакт, а не постоянный минутный сбор. Native GLPI перед сбором связывается с сервером: недоступный PROLOG препятствует независимому накоплению offline hardware history.

Поведение проверено в установленном GLPI 1.19 и [Agent.pm 1.20](https://raw.githubusercontent.com/glpi-project/glpi-agent/1.20/lib/GLPI/Agent.pm), [Target.pm 1.20](https://raw.githubusercontent.com/glpi-project/glpi-agent/1.20/lib/GLPI/Agent/Target.pm). Параметры collector описаны в [официальном CLI](https://glpi-agent.readthedocs.io/en/latest/man/glpi-agent.html).

## Options Considered

1. Только сократить PROLOG: устраняет суточный интервал, но не гарантирует offline collection.
2. Новый постоянно работающий Windows daemon: потребует нового runtime/service packaging и дополнительной поддержки.
3. Task Scheduler SYSTEM, локальный неизменённый GLPI collector и файловая очередь: использует существующий Windows/PowerShell стек и HTTP contract.

## Decision

Выбран вариант 3. Задание запускается каждую минуту и при загрузке, отдельный deadline назначает сбор через 300 секунд + jitter. Сначала отчёт атомарно сохраняется, затем ограниченный batch отправляется с randomized retry. Immutable bytes и существующая серверная SHA-256 дедупликация закрывают повтор после lost ACK. Native daemon отключается после регистрации задания. Пароль остаётся в защищённом реестре; runtime files/data доступны только SYSTEM/Administrators, включая защиту владельца.

Дополнительно PROLOG для старых клиентов становится настраиваемым, default 360 секунд в дробных часах. Это совместимость, а не механизм offline queue для старого installer.

## Reasoning

Сбор больше не зависит от интернет-соединения. Простая bounded очередь без новой зависимости сохраняет прежние отчёты и явно сообщает quota/auth/corruption. Минутный task, file lock, batch=3, jitter и backoff ограничивают одновременную нагрузку. Collector hardware profile, tenant checks и endpoint credentials остаются действующими границами безопасности.

## Consequences and Risks

- At least once delivery; server ACK обязателен для удаления. Полные промежуточные записи восстанавливаются, повреждённые сохраняются отдельно.
- Quota 256 MiB/10000 files приостанавливает новый сбор, сохраняя старые данные. Нет сбора во время сна/выключения.
- Администратор может отключить task; anti-tamper и обход UAC не применяются.
- Server receipt time остаётся временем snapshot; capture time хранится в XML, но пока не является временем UI timeline.
- Частые snapshots увеличивают storage; jitter не отменяет shared NAT rate limit/capacity requirements.
- При неудачном обновлении требуется проверка task и повтор установки; автоматический rollback отсутствует.

## Future Work

Fleet acceptance 3–5 PC, signing/update rollback, отображение offline capture time и retention/capacity по измерениям. Детали: [feature contract](../features/agent-continuous-inventory.md).
