# Технический долг

> **Сверено 2026-10-06.** Текущий статус и границы проверки: [checklist](product/current-project-checklist.md), [аудит](quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Документ содержит только проблемы, подтверждённые текущим репозиторием или результатами эксплуатационной проверки. Это не список пожеланий к продукту.

Приоритеты: `P0` блокирует безопасную эксплуатацию или восстановление; `P1` нужен до расширения пилота; `P2` улучшает сопровождение и масштабирование.

| ID | Приоритет | Область | Подтверждённое состояние | Критерий закрытия |
| --- | --- | --- | --- | --- |
| TD-004 | P1 | Credentials | Bootstrap admin/viewer secrets и legacy shared inventory secret остаются рабочими fallback-механизмами | Named users и per-agent credentials являются обязательным production path; fallback отключаем или строго ограничен и задокументирован |
| TD-005 | P1 | Data governance | Код хранит raw inventory, историю и Vision images, но утверждённые retention/deletion сроки отсутствуют | Принята policy по классам данных и реализованы проверяемые процедуры retention/export/delete |
| TD-006 | P1 | Agent lifecycle | Installer 0.1.8, SYSTEM task/FIFO, сохранение credentials/queue при ручном update и approved re-enrolment реализованы; signing, fleet 3–5 PC, managed rollout и проверенный rollback открыты | Release artifact подписан, update/rollback проверены, credential rotation и re-enrolment приняты на 3–5 pilot-PC |
| TD-007 | P1 | Vision | Pipeline, integration test и scheduled real-model smoke есть; production camera ingestion и quality benchmark отсутствуют | Определён поддерживаемый input, собран репрезентативный dataset, зафиксированы accuracy/latency limits |
| TD-008 | P1 | Release/rollback | Application f4f56e7 развёрнут; API/package version 0.1.0, последний опубликованный installer prerelease 0.1.6. Изолированные restore/migration/recovery испытаны; staging, аварийный failover, release policy и автоматический rollback с данными 0025/0026 открыты | Версия и release notes соответствуют deployed commit; rollback/recovery проверены и задокументированы |
| TD-010 | P2 | Capacity | In-process IP rate limiter, whole-list assets/endpoints и 50-snapshot history window; SQL reads пакетные, load/soak/NAT limits не измерены | Определён deployment limit либо введён shared limiter; зафиксированы нагрузочные границы |

| TD-011 | P1 | Запись/повторы | Обход/часть admin writes не имеют idempotency key; UI блокирует повтор кнопки, но потерянный ответ оставляет неопределённый результат | Для нужных операций определён recovery/idempotency contract и regression на lost response; до этого оператор проверяет history/state перед повтором |
| TD-012 | P1 | Vision recovery | PostgreSQL backup не включает image volume; действующий Oracle profile не содержит ML runtime | До production photos есть tested image backup/object storage и retention; raw DB restore не объявляется восстановлением фотографий |
| TD-013 | P1 | Administration audit | Domain history есть, но нет полного журнала users/grants/credentials/settings и отдельного audit UI | Значимые administrative actions атрибутированы и доступны по scope, с проверенной retention policy |
| TD-014 | P1 | Tenant onboarding | Scoped ADMIN и negative tests есть; отдельного create-organization UI/API и явной platform роли нет | Согласованы полномочия, onboarding и реальная изоляция двух организаций; legacy global fallback ограничен/отключён |
| TD-015 | P1 | UI acceptance | Chromium/reflow/контраст/keyboard/zoom 200% автоматизированы; Firefox/Safari, screen reader, zoom 400% и moderated usability не приняты | Выполнена ручная методика и устранены блокирующие/опасные проблемы |

## Правило ведения

При закрытии пункта сохраните доказательство в tests, runbook, ADR или release notes и удалите строку только после проверки критерия. Новую запись добавляйте, если долг осознанно принят и имеет конкретное последствие; обычную feature request сюда не включайте.
