# AssetGuard MVP v0.1 — аналитическая фиксация

## Статус

Документ сохраняет исходную аналитическую фиксацию до начала разработки. После неё реализованы backend/frontend, PostgreSQL migrations, GLPI privacy-profile/bridge, inventory workflow и Vision demo. Актуальный статус и оставшиеся ограничения ведутся в `docs/product/mvp-completion-checklist.md`.

## Что в ТЗ определено особенно хорошо

- Чёткая ценность продукта: не inventory сам по себе, а объяснимый control workflow.
- Правильное разделение `Asset` и `ManagedEndpoint`.
- Правильное разделение `ComponentObservation` и вероятностного `ComponentIdentity`.
- Immutability raw payload и append-only history позволяют повторно прогонять normalization/diff и проводить аудит.
- Baseline control устраняет главную логическую ошибку многих inventory-проектов: исчезнувший компонент не «забывается» на следующем scan.
- Partial-inventory safety и deterministic dedup защищают от массовых false positive и duplicate incidents.
- Неавтоматическое заключение о краже корректно отделяет telemetry fact от бизнес-вывода.

## Обязательные архитектурные инварианты

1. Raw payload сохранён раньше нормализации и не меняется.
2. Diff ориентируется на active baseline, а не просто на предыдущий snapshot.
3. Snapshot обязан содержать category completeness; неполная категория не участвует в removal detection.
4. Один endpoint может существовать без Asset, один Asset и endpoint — не синонимы.
5. Один наблюдаемый компонент не тождественен одной физической детали.
6. Unresolved incident не сдвигает baseline.
7. Event имеет evidence, deterministic dedup key и confidence.
8. Incident — контейнер workflow, а не синоним технического event.
9. Offline — `REQUIRES_VERIFICATION`, не “stolen/missing”.
10. Canonical model не ссылается на внутренние GLPI IDs.

## Ключевые зависимости и порядок решений

```text
Реальный GLPI payload
        ↓
Direct ingestion feasibility ────────→ A: DirectGlpiAgentAdapter
        │                              B: GLPI 11 + GlpiApiAdapter
        ↓
Фактическая completeness категорий
        ↓
Canonical schema + normalizer rules
        ↓
Identity confidence / invalid values
        ↓
Baseline-safe diff + dedup
        ↓
Incident/history UI
```

Следовательно, нельзя надёжно проектировать окончательный inventory endpoint, canonical fields и diff behavior до spike с реальными payloads.

## Основные риски, которые необходимо подтвердить до реализации

- Может ли GLPI Agent напрямую и поддерживаемо отправлять payload в независимый receiver без имитации GLPI negotiation.
- Как именно агент кодирует FULL/PARTIAL и какие категории гарантированно complete.
- Достаточны ли RAM serial/slot и storage serial на реальных моделях целевых ПК.
- Как выглядят placeholders/OEM defaults в конкретном парке.
- Какая identity переживает reinstall, rename, clone и motherboard replacement.
- Удаётся ли получать monitor EDID стабильно; он не P0 для hard removal detection.
- Каковы scan duration, payload size, retry behavior и нагрузка на слабом железе.

## Скрытые продуктовые решения, которые позже потребуют явной политики

- Что означает `REJECTED` baseline и кто имеет право его выставить.
- Какой severity соответствует RAM/storage removal в разных организациях.
- Должен ли `FALSE_POSITIVE` создавать suppression rule либо закрывать только один event.
- Как event соотносится с incident при нескольких component changes в одном scan.
- Когда и как закрывать incident автоматически после нового baseline — в MVP лучше не автоматически.
- Как хранить/ограничивать сроки raw payload и audit records.

## Reconciliation с предыдущим исследованием

Новое ТЗ согласуется с ранее сохранённым исследованием: GLPI Agent остаётся collector; прямой gateway — hypothesis, GLPI 11 API adapter — fallback; modular monolith + PostgreSQL — целевой MVP. ТЗ существенно уточняет implementation invariants, особенно snapshot completeness, baseline acceptance, fixture coverage и UI workflow. Эти уточнения должны иметь приоритет в последующем implementation plan.

## Workspace inspection

На момент первоначальной фиксации в рабочем каталоге находился только research report. Это историческое наблюдение не описывает текущее состояние репозитория.
