# ADR-002: Явный baseline и доказательный change detection

- **Статус:** принято
- **Дата:** 2026-09-23

## Решение

Baseline меняется исключительно отдельным подтверждённым действием. Сравнение всегда выполняется между ACTIVE baseline и current snapshot. ChangeEvent хранит snapshots, observations, причины сопоставления и confidence в evidence.

## Последствия

- Необработанное изменение не скрывается очередным scan.
- Incident может быть закрыт без автоматического принятия current state как baseline.
- Повторные одинаковые scans должны переиспользовать/обновлять тот же workflow по deterministic dedup key.

