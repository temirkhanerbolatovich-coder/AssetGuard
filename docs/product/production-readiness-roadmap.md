# AssetGuard — roadmap до полноценного production

Этот документ отделяет готовый pilot MVP от требований к системе, которой могут пользоваться несколько школ с реальными данными.

## Этап 1: изоляция доступа

- [ ] Agent credential records: отдельный username + secret для каждого устройства, хранение только password hash.
- [ ] One-time выдача credential администратору, revoke и безопасный re-enrolment без смены ключей других устройств.
- [ ] Migration от legacy общего inventory secret с датой отключения fallback.
- [ ] Tenant model: school/organisation, membership пользователя в tenant, роли `TENANT_ADMIN`, `OPERATOR`, `VIEWER`.
- [ ] Tenant filtering на assets, endpoints, raw inventories, incidents, Vision и Excel import/export.
- [ ] SSO/AD или хотя бы MFA для production admin accounts.

## Этап 2: надёжная эксплуатация

- [ ] Постоянный сервер, домен, TLS acceptance и firewall policy.
- [ ] Automated encrypted off-site backup с ротацией и отдельной политикой хранения ключа.
- [ ] Регулярный isolated restore rehearsal; текущий локальный rehearsal выполнен 2026-09-24.
- [ ] Метрики API, PostgreSQL, disk, backup age, Agent last-seen и failed ingest.
- [ ] Alerting для ответственного сотрудника с правилами escalation.
- [ ] Staging environment и rollback runbook.

## Этап 3: secure software supply chain

- [x] Python dependency vulnerability audit в CI.
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
- [ ] Нормализованная hierarchy `organisation → building → floor → room`, а не только поля Asset.
- [ ] Mobile QR audit, reports, notifications, 1C/AD/helpdesk integrations.
- [ ] Vision production track: object storage, quality gate, multi-frame/RTSP, evaluation dataset и human confirmation.

## Не делать до этапа 1

Не подключать камеры, RTSP, 1С или массовую установку на реальные школы, пока нет tenant isolation, индивидуальных Agent credentials и production backup/monitoring.
