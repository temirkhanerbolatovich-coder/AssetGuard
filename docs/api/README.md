# Границы будущего API

Production URL/transport contract GLPI Agent не фиксируются до technical spike. Уже реализован временный internal adapter boundary `POST /internal/inventories`: он принимает JSON от доверенного адаптера по shared secret и idempotency key, проверяет ограничение размера, сохраняет immutable RawInventory и не нормализует его. Этот endpoint не доказывает совместимость с native GLPI Agent server protocol.

Остальные resource boundaries:

| Resource | Операции MVP |
| --- | --- |
| Assets | list, create, get, update |
| Endpoints | list, get, link to asset |
| Inventories | внутренний ingest endpoint после spike; admin list/get |
| Snapshots | list, get |
| Baseline | get, accept snapshot |
| Changes | list, get |
| Incidents | list, get, decision, resolve |
| Asset history | get |

Admin actions, изменяющие baseline или incident, обязаны оставлять audit/history. Inventory ingest не является публичным admin API.
