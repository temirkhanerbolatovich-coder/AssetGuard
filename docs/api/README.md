# Границы API

Production URL/transport contract GLPI Agent не имитирует нативный GLPI server protocol. Internal adapter boundary `POST /internal/inventories` принимает JSON от доверенного bridge по rotating shared secret и idempotency key, преобразует его через `InventorySourceAdapter`, сохраняет immutable RawInventory, затем синхронно создаёт snapshot, change events и incidents. Текущая реализация — честно названный `TrustedJsonBridgeAdapter`; native GLPI adapter появится только после protocol spike.

Реализованные resource boundaries:

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
| Authentication | login, logout, list/revoke sessions |
| Users | list, create, change role/password/active state |
| Vision rooms | list, scan history, get/save baseline |
| Vision scans | multipart upload/detect, get details, original/annotated image |

Admin actions, изменяющие baseline или incident, обязаны оставлять audit/history. Actor incident decision определяется по аутентифицированной сессии, а не доверяется полю запроса. Inventory ingest не является публичным admin API.

Inventory envelope проходит version-tolerant минимальную проверку (`content` object и обязательный `deviceid` для `GLPI_AGENT`) после сохранения immutable raw evidence. Конкретные source adapters могут расширять этот контракт, не меняя canonical model.

Vision endpoints находятся в существующей admin boundary `/admin/vision/*`. Upload принимает `room_name` и JPEG/PNG `image`; ответ содержит status, counts, comparison, detections с bounding boxes и защищённые URLs изображений. Создание scan и сохранение baseline требуют ADMIN, чтение rooms/scans/images допускает ADMIN или VIEWER.
