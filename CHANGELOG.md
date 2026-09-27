# Changelog

Здесь фиксируются пользовательские, security и эксплуатационные изменения AssetGuard. Незначительные внутренние рефакторинги перечисляются в Git history, но не дублируются в этом файле.

## Unreleased — installer 0.1.7 candidate

### Added

- Отображение версии installer и upstream Agent в Dashboard.
- Предупреждение о неподдерживаемой версии Agent.
- Локальный `%ProgramData%\AssetGuard\agent-lifecycle.jsonl` без секретов.
- Secret-free fleet readiness report для reboot, offline/retry, service recovery, re-enrolment и hardware change.
- Подтверждаемое re-enrolment после переустановки Windows с 30-минутным claim token.
- Admin UI и tenant-scoped API для approve/reject запросов восстановления.

### Security

- Claim token не хранится на сервере в plaintext.
- Подтверждение re-enrolment отзывает прежний активный credential endpoint.
- Исполняемая authorization matrix расширена до 60 защищённых admin operations.

### Deployment note

Код находится в `main`, но installer `0.1.7` ещё не подписан, не опубликован как GitHub Release и не принят на третьем pilot-PC. Repository schema `0025` также не отмечена production runbook как развёрнутая.

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
