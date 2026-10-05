# Changelog

Здесь фиксируются пользовательские, security и эксплуатационные изменения AssetGuard. Незначительные внутренние рефакторинги перечисляются в Git history, но не дублируются в этом файле.

## 2026-10-05 — техническая приёмка UI/UX, этап 5

- Усилен измеренный контраст подписей и границ полей; сплошная клавиатурная обводка больше не теряется при фокусе поля. Диалоги получили доступные имена и ограниченную viewport высоту.
- На коротком экране header/toast находятся в потоке, вкладки сохраняют удобную высоту. Семь новых browser tests проверяют reflow/keyboard/contrast, четыре роли и два tenant, реестр с 216/1000 synthetic assets.
- Локально 102 backend + 16 browser E2E прошли; production/CI приёмка фиксируется отдельно в [протоколе](outputs/assetguard-ui-stage5-2026-10-05.md). [Ручной browser zoom, screen reader, representative performance и usability](docs/testing/ui-acceptance.md) пока не проведены. Без новых dependencies, migrations и изменений Vision.

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

## Unreleased — installer 0.1.7 candidate

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

Installer `0.1.7` остаётся неподписанным и неопубликованным pilot candidate, ещё не принятым на третьем ПК. Исправления стабилизации не добавляют миграций: выкладка применяет уже существующую `0025_agent_reenrolment`.

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
