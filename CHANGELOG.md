# Changelog

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](docs/product/current-project-checklist.md), [аудит](docs/quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Здесь фиксируются пользовательские, security и эксплуатационные изменения AssetGuard. Незначительные внутренние рефакторинги перечисляются в Git history, но не дублируются в этом файле.

## 2026-10-06 — исправление свежести и состояний Agent

- Обзор, реестр, кабинет и администрирование используют вычисляемый сервером `connection_status`; старый сохранённый ONLINE больше не скрывает просроченный отчёт. GET сохраняет БД и историю без изменений.
- Компьютеры без Agent и ожидание первого отчёта получили отдельные состояния/фильтры. Счётчик отсутствия свежих данных включает только STALE/OFFLINE.
- XML-представление `GLPI-Agent_v1.20` распознаётся как поддержанная 1.20; исходная версия evidence сохраняется, неизвестные версии остаются неподдержанными.
- Полная локальная проверка: **170 passed** (148 backend + 22 E2E), JS/diff checks; API/feature/version contracts, README и checklist обновлены. Миграции и зависимости не добавлялись. [Протокол](outputs/assetguard-agent-status-fixes-2026-10-06/report.md). Application `7c45435` опубликован, CI success, production acceptance выполнена после свежего R2 backup/restore. [Протокол публикации](outputs/assetguard-agent-status-publication-2026-10-07.md).

## 2026-10-06 — полный аудит и актуализация документации

- Сверены Git/local/GitHub/server SHA, production image/frontend, schema 0026, health/auth, operational jobs и R2 restore evidence; изучена история связанных чатов.
- Актуализированы README, checklist, architecture/API/security/deployment/testing, UX, Agent/fleet и техдолг; добавлены полный 73-operation API reference, audit report и coverage inventories. QR/mobile audit, Ledger, Agent 0.1.8 и Telegram больше не описываются как будущие этапы.
- Свежая локальная проверка: 145 passed (124 backend + 21 E2E), dependency audit без известных уязвимостей; JS/scripts/Compose проверены. Исторические результаты и восемь ADR сохранены; изменение касается документации и пока локально.

## 2026-10-06 — упрощение навигации и ролей

- Основное меню сокращено до четырёх ежедневных задач: обзор, имущество, инциденты и кабинеты. Администратор получает один вход в управление вместо набора разрозненных разделов.
- Сотрудники, Agent, Telegram, восстановление, импорт и экспорт собраны внутри администрирования. Справка об Agent и экспериментальная проверка по фото открываются из контекста задачи и больше не конкурируют с рабочими разделами.
- Прямые ссылки на административные экраны закрыты для ролей без соответствующих прав; ссылка на экспериментальную проверку по фото для них возвращает в кабинеты.
- Экран входа сокращён до назначения продукта, а подписи Vision и установщика Agent приведены к фактическому статусу (`0.1.8`, неподписанный пилотный кандидат).
- Обзор начинается с текущего состояния и четырёх показателей; задачи и последние события собраны в один рабочий блок. Завершённый onboarding и техническое состояние остаются ниже основной работы.
- В реестре добавление осталось единственным главным действием. Импорт и экспорт перенесены в меню «Ещё», названия представлений и столбцов сокращены и уточнены. [Визуальная проверка](outputs/assetguard-ui-simplification-2026-10-06/report.md).
- В центре инцидентов заголовок сразу называет проблему, а список оставляет одно действие «Открыть». Сравнение и решения находятся в карточке инцидента.
- Кабинеты собраны в дерево «корпус → этаж → кабинет». Создание корпуса открывается в отдельной панели, карточка кабинета сокращена до шести рабочих вкладок, а QR, редактирование и экспериментальная проверка по фото перенесены в меню «Ещё».
- Исправлено наложение административного раздела на текущую страницу: видимость экранов снова полностью определяется маршрутом. [Снимки инцидентов и кабинетов](outputs/assetguard-incidents-rooms-2026-10-06/report.md).
- Администрирование разделено на четыре рабочие вкладки: компьютеры, подключение Agent, восстановление и Telegram. На экране показывается только текущая задача; вкладки поддерживают клавиши стрелок, а сотрудники, импорт и справка остаются отдельными переходами. [Снимки административных экранов](outputs/assetguard-administration-2026-10-06/report.md).
- Пустые состояния Agent и Telegram теперь предлагают следующее действие: подключить компьютер, сбросить фильтры или показать все уведомления. Загрузка доставки использует спокойный skeleton и доступное текстовое состояние. Финальная локальная приёмка всех backend и browser-сценариев: 145 passed. [Итоговый протокол](outputs/assetguard-final-ui-acceptance-2026-10-06/report.md).
- Application `f4f56e7` опубликован в GitHub и принят на действующем Oracle Cloud production. GitHub CI, свежая R2-копия и isolated restore, readiness, schema `0026`, public frontend hashes, monitor и Telegram worker прошли. [Протокол выкладки](outputs/assetguard-ui-release-2026-10-06.md).

## 2026-10-05 — QR-запуск физического обхода

- В карточке кабинета появился печатный QR, который после входа открывает `#room-audit=UUID` и сразу запускает полный обход.
- QR имущества можно считать камерой внутри обхода либо ввести как ссылку/инвентарный номер. Поштучная позиция отмечается найденной; групповой учёт требует ручной проверки результата и количества.
- Черновик обхода восстанавливается после перезагрузки текущей вкладки и очищается после сохранения, сброса или выхода. Чужой QR не изменяет результат.
- Серверный акт, проверки прав, tenant isolation и создание физических инцидентов сохранены. Матрица расширена до 64 защищённых операций; 145 backend/browser тестов прошли.
- Application `1107389` опубликован и развёрнут на production: GitHub CI success, публичные HTML/JS/CSS совпали с Git, schema осталась `0026`, авторизованный QR реального кабинета сформирован. PostgreSQL и Caddy не пересоздавались; pre/post-deploy backup, readiness, зависимости и четыре operational timer прошли.

## 2026-10-05 — полный редизайн UI/UX Ledger

- Светлая рабочая оболочка, навигация и все существующие экраны приведены к одной системе. Golos Text с кириллицей загружается локально; токены текста, поверхностей, контролов и движения заменяют прежнее оформление.
- Реестр отделяет имущество, компьютеры и состояние связи; компактные фильтры, читаемые строки, клавиатурные ссылки и возврат с сохранённым контекстом. Добавление/редактирование открываются в drawer, ошибки и процесс видны в формах.
- Компьютер Agent имеет карточку до связи; аппаратные сведения и история доступны через прежние защищённые API. Сравнение инцидента показывает отдельные поля без вывода о замене по одному имени. Завершённый onboarding скрывается.
- 122 backend + 21 browser E2E прошли; новые проверки font/reflow/reduced motion, отказа/повтора, связи и настоящего browser zoom 200%. Без новых dependencies, migrations или изменения Vision/Agent/Telegram. [Функция и референсы](docs/features/ui-ledger-redesign.md), [приёмка и снимки](outputs/assetguard-redesign-2026-10-05/report.md).

- Application `1f7ff56` принят на production: CI, public checksums/fonts, 63 operations/auth, read-only browser по девяти разделам и реальным карточкам компьютера/инцидента, Agent metadata и прежний Telegram receipt прошли. Название изменения RAM учитывает известные объёмы и единицы измерения; сравнение серийного номера поддерживает оба существующих поля. Database/Caddy сохранены; pre-deploy R2 restore и возврат timers проверены. [Протокол](outputs/assetguard-redesign-2026-10-05/report.md).

## 2026-10-05 — Agent 0.1.8: частый сбор и offline доставка

- Локальный hardware collector работает независимо от сети; защищённая FIFO очередь сохраняет отчёты до XML ACK. Jitter, bounded batch и retry/429 ограничивают нагрузку; revoke и corruption не удаляют прежние данные.
- SYSTEM task при загрузке и каждую минуту назначает сбор через 300 s + 0–60 s; native daemon отключается. PROLOG старых Agent исправлен с 24 h на настраиваемые 360 s при следующем контакте.
- Installer имеет обновление с сохранением ключа и очереди; пароль не попадает в Task/JSONL/EXE. Кандидат неподписан, полный fleet/rollback остаются открыты.
- Локально 122 backend + 16 browser E2E прошли. [Контракт](docs/features/agent-continuous-inventory.md), [ADR-008](docs/decisions/ADR-008-agent-durable-delivery.md), [протокол приёмки](outputs/assetguard-agent-reliability-2026-10-05.md).

## 2026-10-05 — техническая приёмка UI/UX, этап 5

- Аппаратные сводки assets/endpoints читаются пакетно вместо запросов на каждый ПК; список endpoints также использует общий JOIN и однократную проверку room grants. Сохранены partial inventory, окно 50 snapshots на ПК, RAM MiB/bytes, счётчики и tenant/location scope. Шесть новых regression cases защищают поведение и постоянное число SQL reads. Application `0f67995` принят на production: 109 backend + 16 browser E2E, CI и pre/post R2 restore. На сервере SQL 65/105 → 4/4, ответы совпали; [замеры и ограничения](outputs/assetguard-registry-performance-2026-10-05.md). Без новых dependencies и migrations.

- После live-профилирования устранены отдельные SQL endpoint lookups для каждой позиции реестра: LEFT JOIN сохраняет ответ и права, query-budget regression защищает от возврата N+1.

- Усилен измеренный контраст подписей и границ полей; сплошная клавиатурная обводка больше не теряется при фокусе поля. Диалоги получили доступные имена и ограниченную viewport высоту.
- На коротком экране header/toast находятся в потоке, вкладки сохраняют удобную высоту. Семь новых browser tests проверяют reflow/keyboard/contrast, четыре роли и два tenant, реестр с 216/1000 synthetic assets.
- Application `18d6238`: 103 backend + 16 browser E2E, CI, production API/browser и fresh R2 restore прошли; детали в [протоколе](outputs/assetguard-ui-stage5-2026-10-05.md). [Ручной browser zoom, screen reader, representative performance и usability](docs/testing/ui-acceptance.md) пока не проведены. Без новых dependencies, migrations и изменений Vision.

## 2026-10-05 — четвёртый этап UI/UX на production

- Agent: конкретные ПК, последнее соединение, серверный порог STALE, поиск и страницы; привязанный ключ больше не обозначается ONLINE. Быстрые переходы к ключам, восстановлению и Telegram.
- Сотрудники, роли и активность видны рядом с назначениями; формы сохраняют ввод после отказа и блокируют повтор, опасные подтверждения называют объект. Запрос восстановления показывает срок; новый ключ очищается при закрытии.
- ADMIN-only `/admin/notifications` показывает tenant-scoped метаданные, фильтры и страницы: без сообщения, получателя и token. SENT объяснён как принятие Telegram. Матрица расширена до 63 operations, без миграции/Vision/новых зависимостей. [Контракт и ограничения](docs/features/agent-administration-and-delivery.md).

- Application `45d739b`, 102 backend + 9 browser E2E, CI и production UI/API прошли, R2 backup/restore проверены до и после. Существующий Telegram SENT не отправлен повторно. [Приёмка](outputs/assetguard-ui-stage4-2026-10-05.md).

## 2026-10-05 — третий этап UI/UX на production

- Обход требует явно проверить каждую позицию, показывает прогресс, ошибки количества и итог до сохранения; результат доступен в кабинете и истории. Ошибки сохранения оставляют ввод, повторный submit блокируется.
- Import preview показывает scope, исходные строки/страницы, фильтры и выбор; ошибки файла атомарны и привязаны к строкам, итог показывает созданные/обновлённые/исключённые позиции. Mobile preview получил карточки и доступные действия.
- Apply связывает импорт с управляемыми кабинетами; старый файл без колонок локации сохраняет назначение. Дубликаты обычной PDF таблицы отклоняются вместо молчаливого объединения. Без новых миграций и изменений Vision. [Описание и ограничения](docs/features/rooms-inspection-and-import.md).
- Исправлена повторная нормализация типов: принтер/проектор после проверки распознанной строки сохраняет тип вместо перехода в Other; canonical типы совместимы с повторным импортом.

- Application `2ae4b01`: 101 backend + 8 browser E2E, CI, production browser/API и backup/restore. [Протокол](outputs/assetguard-ui-stage3-2026-10-05.md).

## 2026-10-05 — второй этап UI/UX на production

- Приоритетные задачи в обзоре; реестр с количеством/единицей, совместными фильтрами, сортировкой и страницами по 20 записей; возврат из карточки сохраняет список.
- Единый центр технических и физических инцидентов, фильтры source/room/date, карточка исходного обхода, решение и PDF-акт. Имущество без Agent показывается как ручной учёт.
- Два защищённых GET физических инцидентов, tenant/location negative tests; access matrix содержит 62 операции. Схема БД и Vision не изменены. [Описание](docs/features/registry-and-incident-center.md).

- Application `c254125`: 97 backend + 7 browser E2E, CI, authenticated production UI и read-only API приёмка. [Протокол](outputs/assetguard-ui-stage2-2026-10-05.md).

## 2026-10-05 — первый этап UI/UX на production

- Отдельный вход, профиль/контекст, адаптивное меню, loading/error/retry и защита от поздних ответов; очищается сессия, именованный выход запрашивает серверный revoke.
- Исправлен перенос onboarding-ссылки на узком экране. Secret scan использует штатный GitHub token с прежними read-only permissions для устранения anonymous API rate-limit.
- Application `d8f6a63`: 96 backend + 6 browser E2E, CI success, публичная browser/API проверка и backup/restore. [Протокол](outputs/assetguard-ui-stage1-2026-10-05.md).

## Исторический этап — installer 0.1.7 candidate

### Added

- Уведомления о новых технических/физических инцидентах: PostgreSQL outbox, organization-scoped Telegram worker, retry/429 и подтверждение назначения; migration `0026`.
- Operations counters pending/retrying, мониторинг failed notification job, русские сообщения и ссылки в Telegram.
- Отдельное ТЗ UI/UX с исследованными примерами, критериями доступности и пятью этапами модернизации.

- Отображение версии installer и upstream Agent в Dashboard.
- Предупреждение о неподдерживаемой версии Agent.
- Локальный `%ProgramData%\AssetGuard\agent-lifecycle.jsonl` без секретов.
- Secret-free fleet readiness report для reboot, offline/retry, service recovery, re-enrolment и hardware change.
- Подтверждаемое re-enrolment после переустановки Windows с 30-минутным claim token.
- Admin UI и tenant-scoped API для approve/reject запросов восстановления.
- Структурированные quantity/unit/tracking_mode в Excel/PDF/OCR import preview/apply и Excel export; сохранение остатков и локаций после учётных актов при повторном импорте.

### Security

- Claim token не хранится на сервере в plaintext.
- Подтверждение re-enrolment отзывает прежний активный credential endpoint.
- Исполняемая authorization matrix расширена до 60 защищённых admin operations.
- Проверка endpoint/organization Agent до доменных изменений, включая duplicate; первая привязка и snapshot сохраняются одной транзакцией.
- Исправлен tenant fallback при Excel/PDF import без колонки организации; preview/create/update используют только разрешённый scope.

### Fixed

- Ошибочная индикация успешного входа после неудачной загрузки; сохранённый session token больше не помещается в password input.
- Поздние ответы чтения после выхода/смены карточки; ограничение ожидания JSON reads/login/logout, обработка expiry и серверный revoke именованной сессии.

- Operations freshness считается по last_seen даже до maintenance; просроченные ONLINE/REQUIRES_VERIFICATION попадают в stale.
- Monitor очищает fingerprint после recovery, проверяет Telegram acceptance и повторяет попытку после отказа; malformed metrics становятся alert condition.
- Scheduled/manual Grounding DINO smoke job получает обязательные shared settings без изменения detector/model.

### Deployment note

`0b90607` развёрнут 2026-10-05 по времени клиента: schema `0026`, 96 backend tests и 2 browser E2E, GitHub CI, isolated upgrade/downgrade и pre/post R2 restore прошли. Telegram подтвердил тест из новой очереди, пользователь получил его, повтор подавлен. [Протокол Telegram](outputs/assetguard-telegram-2026-10-05.md). Эта версия не меняет Vision и frontend runtime.

Application commit `93ff8ed` опубликован в `main` и развёрнут 2026-10-04: production schema `0025`, публичный UI, защищённые re-enrolment routes и monitor проверены. Push/manual GitHub CI прошли, включая 80 backend tests, 2 browser E2E и реальную модель. Перед выкладкой выполнены encrypted R2 restore и изолированный upgrade/downgrade/re-upgrade с запуском прежнего API; Telegram подтвердил test alert, повтор подавлен. Подробности и ограничения отката — в [протоколе выкладки](outputs/assetguard-release-2026-10-04.md).

На этом этапе installer `0.1.7` был неподписанным и неопубликованным pilot candidate, ещё не принятым на третьем ПК. Исправления стабилизации не добавляли миграций: выкладка применяла уже существующую `0025_agent_reenrolment`. Текущий candidate `0.1.8` и schema `0026` описаны в записях 5–6 октября и основном checklist.

## [v0.1.6] — 2026-09-27

- Опубликован pilot installer и SHA-256.
- Новые установки закреплены на GLPI Agent 1.20; Agent 1.19 сохранён как совместимый.
- Неизвестная версия Agent отклоняется до отдельного contract test.
- Зафиксированы production deployment, encrypted R2 backup/restore rehearsal и server monitoring.

## [v0.1.0-demo] — 2026-09-23

- Первый демонстрационный релиз с native GLPI Agent transport.
- Raw inventory, snapshot, explicit baseline, hardware change, incident и history workflow.
- AssetGuard Vision demo: upload, detection, counts, room baseline и warning comparison.

[v0.1.6]: https://github.com/temirkhanerbolatovich-coder/AssetGuard/releases/tag/v0.1.6
[v0.1.0-demo]: https://github.com/temirkhanerbolatovich-coder/AssetGuard/releases/tag/v0.1.0-demo
