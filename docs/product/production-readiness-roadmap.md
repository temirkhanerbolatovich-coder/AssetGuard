# AssetGuard — roadmap до полноценного production

Этот документ отделяет готовый pilot MVP от требований к системе, которой могут пользоваться несколько школ с реальными данными.

## Этап 1: изоляция доступа

- [x] Agent credential records: отдельный username + secret для каждого устройства, хранение только password hash.
- [x] One-time выдача credential администратору и revoke без смены ключей других устройств.
- [ ] Self-service re-enrolment flow с подтверждением администратора.
- [ ] Migration от legacy общего inventory secret с датой отключения fallback.
- [~] Tenant model: school/organisation, tenant-bound users/credentials и job roles `LOCATION_MANAGER`/`INVENTORY_CLERK` есть; отдельная полномочная модель `TENANT_ADMIN`/`OPERATOR` ещё не выделена.
- [~] Tenant filtering внедрён на assets, endpoints, raw inventories, incidents, Vision, Excel/PDF и identity API; нужен полный matrix-тест всех admin routes перед multi-school rollout.
- [ ] SSO/AD или хотя бы MFA для production admin accounts.

## Этап 2: надёжная эксплуатация

- [x] Постоянный Oracle Cloud server, DuckDNS, публичный TLS endpoint и ограничивающие сетевые правила проверены 2026-09-25.
- [x] Windows Task Scheduler запускает daily encrypted backup и weekly isolated restore rehearsal через PowerShell 7; R2 copy и retention настроены на 14 дней локально / 30 дней off-site. Обе задачи принудительно запущены 2026-09-27 и завершились с `LastTaskResult=0`.
- [x] Cloudflare R2 повторно авторизован account token с доступом только к `assetguard-backups`; ручной encrypted upload → download → isolated restore завершён `PASS` 2026-09-27.
- [x] Постоянные Linux timers запускают daily backup, weekly restore rehearsal и monitor каждые 5 минут. Ручная server-приёмка 2026-09-27: backup upload и isolated restore `PASS` (`0024`, `assets=211`, `endpoints=1`).
- [x] Server monitor проверяет readiness, Compose services, disk, backup age/job failures, Agent last-seen, failed ingest и identity conflicts.
- [x] Telegram server alerting принят 2026-09-27: test alert принят API, второй одинаковый запуск подавлен, normal run healthy; неизменившаяся проблема повторяется через 4 часа.
- [ ] Staging environment и rollback runbook.

## Этап 3: secure software supply chain

- [x] Python dependency vulnerability audit в CI: проверяет точные установленные версии, включая CPU-сборку PyTorch, без повторного скачивания из неподходящего PyPI-индекса.
- [x] Dependabot для Python и GitHub Actions.
- [x] Secret scanning всей Git-истории в CI и локальный pre-commit hook.
- [ ] Protection rules на `main` с обязательным успешным CI.
- [ ] SAST, container image scan и SBOM release artifact.
- [ ] Подписанные Windows installer/release artifacts и политика обновления Agent.
- [ ] Внешний penetration test перед работой с несколькими организациями.

## Этап 4: fleet validation

- [ ] Тест на нескольких реальных PC: cold boot, offline/retry, reimage, replacement hardware, service recovery и agent update.
- [ ] Нагрузочный тест ingest и dashboard на целевом количестве endpoints.
- [ ] Contract test для каждого нового GLPI Agent release.

## Этап 5: data governance и продукт

- [ ] Утверждённая data inventory, retention/deletion policy для raw inventory и Vision images.
- [ ] Согласованный legal/security review для школ и выбранного места хранения данных.
- [x] Нормализованная hierarchy `organisation → building → floor → room`; основные location grants enforced на сервере.
- [~] QR-коды карточек, location reports и полный физический обход из карточки кабинета доступны; QR-запуск mobile audit, in-app notifications и 1C/AD/helpdesk integrations ещё нужны.
- [ ] Vision production track: object storage, quality gate, multi-frame/RTSP, evaluation dataset и human confirmation.

## Не делать до этапа 1

Не подключать камеры, RTSP, 1С или массовую установку на реальные школы, пока нет tenant isolation, индивидуальных Agent credentials и production backup/monitoring.
