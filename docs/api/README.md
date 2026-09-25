# Границы API

Доступны две transport boundaries. `POST /internal/inventories` принимает JSON от доверенного bridge по rotating shared secret и idempotency key. `POST /glpi-agent` реализует наблюдаемый GLPI Agent 1.19 XML flow `PROLOG → SEND → INVENTORY` с HTTP Basic authentication. `TrustedJsonBridgeAdapter` и `DirectGlpiAgentAdapter` преобразуют transport payload в общий canonical envelope, сохраняют immutable RawInventory и запускают один snapshot/change/incident workflow.

Реализованные resource boundaries:

| Resource | Операции MVP |
| --- | --- |
| Assets | list, create, get, update |
| Endpoints | list, get, link to asset |
| Inventories | внутренний ingest endpoint после spike; admin list/get |
| Native GLPI Agent | authenticated XML PROLOG/INVENTORY endpoint |
| Snapshots | list, get |
| Baseline | get, accept snapshot |
| Changes | list, get |
| Incidents | list, get, decision, resolve |
| Asset history | get |
| Authentication | login, logout, list/revoke sessions |
| Users | list, create, change role/password/active state |
| Location access | grant/remove VIEWER or EDITOR at building/floor/room scope; location tree and room reports respect grants |
| Room inspections | list and complete immutable physical inspection acts; every asset must be marked present, missing or damaged and write access requires ADMIN or an EDITOR grant |
| Physical incidents | automatic incident for every missing/damaged inspection item; ADMIN/EDITOR can investigate or resolve it as move, repair, write-off or false positive |
| Vision rooms | list, scan history, get/save baseline |
| Vision scans | multipart upload/detect, get details, original/annotated image |
| Asset import/export | Excel and PDF export; Excel/PDF preview and confirmed selective apply |

Admin actions, изменяющие baseline или incident, обязаны оставлять audit/history. Actor incident decision определяется по аутентифицированной сессии, а не доверяется полю запроса. Inventory ingest не является публичным admin API.

Inventory envelope проходит version-tolerant минимальную проверку (`content` object и обязательный `deviceid` для `GLPI_AGENT`) после сохранения immutable raw evidence. Конкретные source adapters могут расширять этот контракт, не меняя canonical model.

Vision endpoints находятся в существующей admin boundary `/admin/vision/*`. Upload связывает scan с кабинетом школьной иерархии и принимает JPEG/PNG `image`; результат содержит status, counts, comparison, detections с bounding boxes и защищённые URLs изображений. Доступ к scans/images проходит через локационный grant. Legacy rooms без однозначной связи видны только ADMIN.

`POST /admin/assets/import.xlsx` и `/admin/assets/import.pdf` без `apply=true` возвращают read-only предпросмотр всех распознанных позиций (`items`). При подтверждении `apply=true` те же файлы отправляются повторно; multipart-поле `exclude_row` может повторяться и содержит нулевые индексы исключаемых позиций. Только этот второй запрос записывает оставшиеся строки.

`GET /admin/locations/rooms/{room_id}/inspections` возвращает последние акты доступного кабинета. `POST` на тот же адрес завершает обход атомарно: запрос обязан содержать ровно один результат для каждой текущей позиции кабинета. Для `MISSING` и `DAMAGED` требуется количество от 1 до учётного остатка; для `PRESENT` количество проблемных единиц равно нулю. Исполнитель определяется по аутентифицированной сессии, а результат добавляется в историю актива и кабинета.

Каждая строка `MISSING` или `DAMAGED` автоматически создаёт физический инцидент, связанный с актом, активом и кабинетом. `POST /admin/locations/physical-incidents/{incident_id}/decision` принимает обязательный комментарий и действие `INVESTIGATE`, `MOVE`, `REPAIR`, `WRITE_OFF` или `FALSE_POSITIVE`. Первое оставляет инцидент `UNDER_REVIEW`, остальные закрывают его. Actor берётся из сессии; решения append-only. Действие фиксирует управленческое решение, но не перемещает и не списывает карточку имущества автоматически.
