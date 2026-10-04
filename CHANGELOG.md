# Changelog

Здесь фиксируются пользовательские, security и эксплуатационные изменения AssetGuard. Незначительные внутренние рефакторинги перечисляются в Git history, но не дублируются в этом файле.

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
