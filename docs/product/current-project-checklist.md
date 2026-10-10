# AssetGuard — актуальный статус и чек-лист

> **Эксплуатационная пауза 2026-10-10 21:44:03 UTC+5.** AssetGuard остановлен по запросу владельца. Runtime отсутствует; пять server timers (Telegram monitor/outbox, backup/restore, DuckDNS) и локальный Telegram monitor выключены. TimScheduleBot работает на той же VM. [Протокол](../../outputs/assetguard-shutdown-2026-10-10.md). Датированные результаты ниже сохраняются как историческая приёмка.

> **Сверено 2026-10-07.** Текущий статус и границы проверки: [checklist](current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Дата сверки: **7 октября 2026 года**, Asia/Qyzylorda (UTC+5). Основание: текущий код, migrations, тесты, GitHub API, read-only production и история связанных чатов. [Полный аудит и границы проверки](../quality/project-audit-2026-10-06.md).

## Проверенная точка продолжения

| Показатель | Подтверждённый результат |
| --- | --- |
| Application commit | `7c45435971329cabd6382466eadca8a1540ade7d` опубликован в `main`; документация приёмки зафиксирована отдельным docs commit |
| Последняя принятая application | `7c45435971329cabd6382466eadca8a1540ade7d`; принято 2026-10-06, runtime остановлен 2026-10-10 |
| Сохранённая API image | `sha256:1a98957a3ef6829a3281d32c5e9130157a4e73feff730e2e4a165da7902beda1`; rollback tag `assetguard-api:rollback-pre7c45435-20261006` |
| Схема | 26 migrations; `0026_telegram_notifications (head)` локально и на сервере |
| Автоматические тесты | Последний полный локальный прогон (2026-10-06): **148 backend + 22 browser E2E = 170 passed**, 125.79s |
| Публичный сервер | Остановлен по запросу владельца 2026-10-10; прежние HTTP acceptance относятся к 2026-10-06 |
| CI опубликованного состояния | [Application CI](https://github.com/temirkhanerbolatovich-coder/AssetGuard/actions/runs/37512336108): success; результаты production acceptance зафиксированы отдельным docs commit |
| Admin API | **64 защищённые операции**, 57 путей; 29 ADMIN-only и 35 Viewer-level с resource scope |
| Installer | Опубликованный prerelease `0.1.6`; `0.1.8` собран и проверен ограниченно, **NotSigned**, не опубликован как новый release |
| Backup/restore | `assetguard-production-20261006-183238.sql.agbackup`, isolated restore PASS: schema `0026`, assets=220, endpoints=11; server jobs success |

Документационный аудит и исправления свежести Agent, состояний подключения и XML-представления версии 1.20 опубликованы; application `7c45435` принят на сервере. Полный локальный прогон — 170 cases, GitHub CI — success. [Протокол публикации](../../outputs/assetguard-agent-status-publication-2026-10-07.md). [Протокол и снимки](../../outputs/assetguard-agent-status-fixes-2026-10-06/report.md). Package/API version `0.1.0` и installer version `0.1.8` — разные значения.

Read-only срез **2026-10-06 17:29:16 UTC+5 / 12:29:16 UTC**: **220 assets, 11 endpoints, 389 raw inventories, 389 snapshots; 6 ONLINE / 5 STALE, 0 identity conflicts, 0 failed ingest**. Telegram: 3 SENT, ожидающих записей на этом срезе нет. Все четыре timers (monitor, notifications, backup, restore rehearsal) активны; последние jobs — success/0. На дату среза inventory counts продолжали расти. Это историческое состояние сервера, а не fleet acceptance пяти stale PC.

## Итоговая готовность

**Рабочий pilot MVP.** Реестр, Agent ingestion, baseline/инциденты, физические операции, QR, imports, Ledger UI, Telegram и серверное восстановление реализованы. Массовый multi-school rollout требует fleet, secure release, governance, проверенного onboarding/isolation и эксплуатационной приёмки.

Статусы: ✅ работает и проверено в указанном объёме; 🟡 частично/приёмка ограничена; ⛔ отсутствует.

## Реализовано и ранее проверено

| Область | Статус | Реализация и доказательство |
| --- | --- | --- |
| Backend/БД | ✅ | FastAPI, SQLAlchemy, PostgreSQL 17, Alembic 0001–0026; migrations в disposable БД и live head |
| Raw evidence | ✅ | Исходный payload/hash/время и source immutable; processing metadata может меняться по workflow, delete блокируется trigger |
| GLPI transport | ✅ | Native XML 1.19/1.20 и trusted JSON bridge; authentication, partial/full, duplicates и negative scope tests |
| Аппаратная identity | ✅ | Matching, hardware snapshots, CPU/RAM/storage/GPU/monitor metadata, conflict handling |
| Baseline/изменения | ✅ | Только явное принятие baseline; evidence-aware RAM/storage diff и dedup; PARTIAL не создаёт ложных removals |
| Реестр | ✅ | Individual/grouped accounting, quantity/unit, категории, связь Asset—Endpoint, карточка компьютера до связи |
| Локации/доступ | ✅ foundation | Организация → корпус → этаж → кабинет; named users, sessions, четыре роли, VIEWER/EDITOR grants, 64-operation registry и tenant/location tests |
| Credentials/re-enrolment | ✅ | One-time выдача, hashes, revoke, 30-minute claim request, ADMIN approval и сохранение endpoint/history |
| Физический обход | ✅ | Явный результат каждой позиции, review перед POST, immutable акт, physical incidents и Telegram outbox в одной транзакции |
| Перемещение/списание | ✅ | Полные/частичные grouped operations, source/destination access, history и PDF-акты |
| Excel/PDF/OCR | ✅ для поддержанных форм | Read-only preview, source row/page, выбор строк, атомарный отказ, canonical rooms; акты имеют приоритет над старой ведомостью |
| QR имущества/кабинета | ✅ | `#asset=UUID`, `#room-audit=UUID`, camera BarcodeDetector при поддержке, manual fallback; grouped quantity подтверждает человек |
| Черновик обхода | ✅ в текущей сессии | `sessionStorage` по пользователю/кабинету; reload recovery, очистка после save/reset/logout; не offline/PWA |
| Ledger UI | ✅ автоматическая часть | Четыре рабочих раздела, task tabs администратора, loading/error/empty, управляемые формы, mobile/reflow/keyboard/reduced motion и Chromium zoom 200% |
| Telegram | ✅ реализован; отправка остановлена | Transactional outbox, minute worker, tenant chat routing, retry/429 и SENT после acceptance; server monitor раз в 5 минут |
| Backup/restore | ✅ PostgreSQL | AES-256-GCM, R2 upload/download, retention 14 local / 30 off-site days, isolated restore; Vision files исключены |
| CI/supply chain | ✅ foundation | PostgreSQL/API/E2E, pip check/audit, Gitleaks, script/JS/Compose validation; отдельный scheduled/manual real-model job |
| Vision | ✅ локальный demo / 🟡 production | Photo → detections/counts → explicit room baseline → WARNING; последний документированный real-model smoke 4 октября, 23 detections |

## Что реализовано частично

| Область | Уже есть | Открытая граница |
| --- | --- | --- |
| Agent 0.1.8 | SYSTEM task, независимый collector, bounded FIFO, jitter/ACK/backoff; реальные автоматические циклы одного PC и controlled lost ACK | 3–5 PC, физический network/reboot/reimage, финальная readiness установка, update/rollback и signing |
| Multi-tenant | Scoped ADMIN, grants, negative tests двух синтетических организаций | Явная platform/onboarding модель, реальная приёмка двух организаций, миграция/отключение legacy global/shared fallback |
| Мониторинг | Readiness, disk, jobs, ingest, aggregated Agent status и dedup | Индивидуальные переходы Agent, on-call policy, метрики/централизованные логи |
| Эксплуатация | Production, retained rollback images, isolated migration/recovery и restore | Staging, настоящий API-failure/failover drill, безопасная rollback automation и RTO/RPO |
| Импорт/отчётность | Supported formats, row errors, room reports, exports/акты | Mapping wizard, дополнительные реальные формы, school summaries и scheduled reports |
| UX | Автоматическая регрессия, lab performance, scoped operations | Firefox/Safari, NVDA/VoiceOver, zoom 400%, настоящие телефоны, representative performance и moderated usability |
| Данные | Immutable evidence и protected queue/images | Утверждённые retention/export/delete правила; Vision image backup/object storage; notification/Agent queue retention |

## Пока отсутствует

- ⛔ Подписанный release Agent 0.1.8 и автоматическое управляемое обновление/rollback.
- ⛔ UI/API создания организации как отдельный onboarding workflow; есть scoped список и существующие import/legacy bootstrap пути.
- ⛔ MFA/SSO/AD, интеграции 1С/helpdesk и in-app notifications.
- ⛔ Общий admin audit экран для users/grants/credentials/settings.
- ⛔ Отдельный offline/PWA/mobile app и межсессионная синхронизация обхода.
- ⛔ SAST, container image scan, SBOM, protection rules `main` и внешний pentest.
- ⛔ Multi-school load/soak acceptance и серверная пагинация assets/endpoints.
- ⛔ Production Vision inference host, camera/RTSP, multi-frame quality gate, evaluation dataset и mapping detection → конкретный Asset.

## Ближайший порядок работы

### P0 — перед расширением пилота

1. **Fleet 0.1.8 на 3–5 реальных Windows-PC:** все фазы [протокола](../operations/agent-fleet-pilot.md), automatic captures, reboot, физический offline/FIFO, lost ACK, task recovery, hardware change, revoke/re-enrolment, update и rollback. Проверить пять stale PC по месту, не исправлять counters вручную.
2. **Secure release:** code-signing certificate, подпись/проверка EXE, checksum, реальный update/rollback; затем publication нового prerelease/release. Текущий checksum известен, подписи нет.
3. **Data governance:** владелец, минимизация/доступ/хранение/экспорт/удаление по классам данных; отдельное решение для фотографий и очередей.
4. **Две организации:** onboarding и полномочия platform/school admin, controlled isolation acceptance, перевод устройств на отдельные credentials и дата отключения legacy fallback.
5. **Ручная UI-приёмка:** [методика](../testing/ui-acceptance.md), 3–5 представителей ролей, цель ≥90% применимых задач без помощи и отсутствие опасных ошибок; результатов такого теста пока нет.
6. **Staging/recovery:** восстановление только из R2, намеренный сбой API и alert, application rollback с учётом данных `0025`/`0026`, измерение RTO/RPO.

### P1 — следующий продуктовый и эксплуатационный релиз

1. Единый административный audit log и доступный экран аудита.
2. Сводные school reports, operation filters и scheduled PDF/Excel.
3. Mapping wizard, dedup review и дополнительные форматы ведомостей.
4. MFA/SSO, branch protection, SAST/container scan/SBOM и proxy rate limit.
5. Representative performance, capacity/retention/NAT tests; выбор server pagination.
6. Согласование version/release policy приложения и лицензии проекта.

### P2 — Vision и интеграции

1. Vision dataset/accuracy, inference host, object storage/image backup и retention.
2. Quality gate/multi-frame/human confirmation, затем RTSP и asset mapping.
3. 1С, AD/helpdesk и другие согласованные интеграционные контракты.

## Демонстрация после локального запуска

Production остановлен. Следующий сценарий доступен после локального запуска; возобновление сервера требует нового запроса владельца.

1. Войти в Ledger, показать имущество и кабинет.
2. Показать Excel/PDF preview без записи, QR кабинета и начало обхода.
3. В учебной организации сохранить контролируемый обход и разобрать physical incident/акт.
4. Открыть компьютер, baseline, raw evidence и аппаратное сравнение.
5. Показать delivery metadata Telegram и объяснить SENT как acceptance, не прочтение.
6. Vision демонстрировать локально на demo-паре; WARNING не доказывает пропажу/кражу.

## Правило поддержки

После изменения поведения обновляйте этот checklist, профильный feature/runbook, README и changelog; запускайте затронутые проверки. Публикация/CI/deployment фиксируются только после фактического выполнения. При schema change нужны fresh backup и migration/recovery проверки. Исторические SHA, test counts и server snapshots сохраняйте с исходной датой; текущее состояние сверяйте заново.
