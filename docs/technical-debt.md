# Технический долг

Документ содержит только проблемы, подтверждённые текущим репозиторием или результатами эксплуатационной проверки. Это не список пожеланий к продукту.

Приоритеты: `P0` блокирует безопасную эксплуатацию или восстановление; `P1` нужен до расширения пилота; `P2` улучшает сопровождение и масштабирование.

| ID | Приоритет | Область | Подтверждённое состояние | Критерий закрытия |
| --- | --- | --- | --- | --- |
| TD-001 | P0 | Backup/DR | R2 backup/restore rehearsal блокируется `SignatureDoesNotMatch`; локальная crypto interoperability покрыта тестом | Успешный зашифрованный upload, download и restore rehearsal из R2 с зафиксированным результатом |
| TD-002 | P1 | Operations | Linux backup, restore и monitoring scripts существуют, но репозиторий не подтверждает их установку на постоянном сервере | Timers/services установлены, alerts доставляются, runbook содержит проверенный результат |
| TD-003 | P0 | Authorization | Роли и scope tests существуют, но полный allow/deny matrix всех admin routes не автоматизирован | Каждая защищённая route/role комбинация отражена в актуальной матрице и negative tests |
| TD-004 | P1 | Credentials | Bootstrap admin/viewer secrets и legacy shared inventory secret остаются рабочими fallback-механизмами | Named users и per-agent credentials являются обязательным production path; fallback отключаем или строго ограничен и задокументирован |
| TD-005 | P1 | Data governance | Код хранит raw inventory, историю и Vision images, но утверждённые retention/deletion сроки отсутствуют | Принята policy по классам данных и реализованы проверяемые процедуры retention/export/delete |
| TD-006 | P1 | Agent lifecycle | Установщик и per-agent credentials есть; централизованная signing/release и подтверждённая ротация fleet отсутствуют | Release artifact подписан, версия прослеживается, credential rotation проверена на pilot fleet |
| TD-007 | P1 | Vision | Pipeline, integration test и scheduled real-model smoke есть; production camera ingestion и quality benchmark отсутствуют | Определён поддерживаемый input, собран репрезентативный dataset, зафиксированы accuracy/latency limits |
| TD-008 | P1 | Release/rollback | Production Compose описан, но tag `v0.1.0-demo` не отражает текущее состояние, version остаётся `0.1.0`; автоматизированного rollback rehearsal нет | Версия и release notes соответствуют deployed commit; rollback/recovery проверены и задокументированы |
| TD-009 | P2 | Documentation | Часть старых документов расходится с кодом: source layout заканчивает migrations на `0009`, Vision analysis утверждает отсутствие location hierarchy; `docs/data` исключается общим правилом `.gitignore` | Устаревшие документы помечены или синхронизированы; все ссылки CI-проверяемы; docs files не скрываются случайным ignore rule |
| TD-010 | P2 | Capacity | In-process rate limiter хранит состояние одного API-процесса; нагрузочные тесты отсутствуют | Определён deployment limit либо введён shared limiter; зафиксированы нагрузочные границы |

## Правило ведения

При закрытии пункта сохраните доказательство в tests, runbook, ADR или release notes и удалите строку только после проверки критерия. Новую запись добавляйте, если долг осознанно принят и имеет конкретное последствие; обычную feature request сюда не включайте.
