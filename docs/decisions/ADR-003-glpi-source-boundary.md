# ADR-003: GLPI Agent как неизменяемый collector

- **Статус:** принято с технической проверкой
- **Дата:** 2026-09-23

## Решение

Primary path: GLPI Agent отправляет inventory в AssetGuard Inventory Gateway. Реализуется `DirectGlpiAgentAdapter` только после подтверждения реального протокола и payload.

Fallback path: GLPI Agent → GLPI 11 → GLPI API → `GlpiApiAdapter` → AssetGuard Core.

## Неподвижные границы

- GLPI Agent не модифицируется.
- AssetGuard не использует внутреннюю БД GLPI как свою основную БД.
- Canonical model AssetGuard не зависит от внутренних GLPI ID.
- Выбор пути зависит от результатов technical spike, а не от предположений.

