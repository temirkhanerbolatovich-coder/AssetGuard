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
- [~] Automated encrypted backup + weekly isolated restore rehearsal доступны через Windows Task Scheduler; свежая локальная копия проверена восстановлением 2026-09-24. Off-site ротация и отдельная политика хранения ключа ещё не настроены.
- [x] Изолированная локальная restore rehearsal: зашифрованная копия восстановлена в отдельный временный PostgreSQL и сравнена с текущей БД; off-site recovery остаётся незакрытым.
- [~] `/health` и `/health/ready` готовы; локальный Windows monitor проверяет disk, Agent last-seen, failed ingest и identity conflicts. Нужен постоянный серверный сбор метрик, включая backup age.
- [~] Telegram alerting с дедупликацией работает из локального Windows-контура; нужны серверное расписание и правила escalation.
- [ ] Staging environment и rollback runbook.

## Этап 3: secure software supply chain

- [x] Python dependency vulnerability audit в CI: проверяет точные установленные версии, включая CPU-сборку PyTorch, без повторного скачивания из неподходящего PyPI-индекса.
- [x] Dependabot для Python и GitHub Actions.
- [ ] Secret scanning / pre-commit hook и protection rules на main.
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
