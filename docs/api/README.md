# Границы API

> **Сверено 2026-10-07.** Текущий статус и границы проверки: [checklist](../product/current-project-checklist.md), [аудит](../quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Доступны две transport boundaries. `POST /internal/inventories` принимает JSON от доверенного bridge по rotating shared secret и idempotency key. `POST /glpi-agent` реализует наблюдаемый GLPI Agent 1.19/1.20 XML flow `PROLOG → SEND → INVENTORY` с HTTP Basic authentication. `TrustedJsonBridgeAdapter` и `DirectGlpiAgentAdapter` преобразуют transport payload в общий canonical envelope, сохраняют immutable RawInventory и запускают один snapshot/change/incident workflow.

На 6 октября OpenAPI содержит **73 HTTP operations на 66 путях**; `/admin` — **64 операции на 57 путях**, 29 ADMIN-only и 35 Viewer-level. [Полный method/path реестр](route-reference.md) сверен с OpenAPI и executable registry; [resource/role scope](../security/admin-route-access-matrix.md) применяется дополнительно. `GET /glpi-agent` не объявлен: ожидаемый browser 404; unauthenticated XML POST — 401.

Реализованные resource boundaries:

В опубликованном application `7c45435` от 2026-10-06 добавлено read-only поле `connection_status` в endpoint summaries (`GET /admin/endpoints`, `GET /admin/assets` и `GET /admin/assets/{id}`), `GET /admin/endpoints/{id}` и `agents[]` в `GET /admin/locations/rooms/{id}/workspace`. Оно вычисляется по `last_seen_at` и серверному порогу; `IDENTITY_CONFLICT`/`OFFLINE` имеют приоритет, затем `STALE`, иначе сохранённый статус. Исходное поле `status` сохраняется, GET не меняет БД/историю. Контракты доступа и число маршрутов не меняются. [Политика и обратная совместимость](../features/agent-administration-and-delivery.md), [регрессия](../../outputs/assetguard-agent-status-fixes-2026-10-06/report.md).

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
| Authentication | login, logout, list/revoke sessions; per-Agent credentials; approved re-enrolment after Windows reinstall |
| Users | list, create, change role/password/active state |
| Location access | grant/remove VIEWER or EDITOR at building/floor/room scope; location tree and room reports respect grants |
| Room inspections | list and complete immutable physical inspection acts; every asset must be marked present, missing or damaged and write access requires ADMIN or an EDITOR grant |
| Physical incidents | tenant/location-scoped list and original inspection evidence/detail reads; automatic incident for every missing/damaged inspection item; ADMIN/EDITOR can investigate or resolve it as move, repair, write-off or false positive |
| Vision rooms | list, scan history, get/save baseline |
| Vision scans | multipart upload/detect, get details, original/annotated image |
| Notifications | ADMIN-only tenant delivery metadata; фильтры PENDING/RETRYING/SENT, pagination; чтение не отправляет сообщения |
| Room QR | Tenant/location-scoped SVG со ссылкой `#room-audit=UUID`; создаёт ссылку, а не акт обхода |
| Asset import/export | Excel and PDF export; Excel/PDF preview and confirmed selective apply |

Admin actions, изменяющие baseline или incident, обязаны оставлять audit/history. Actor incident decision определяется по аутентифицированной сессии, а не доверяется полю запроса. Inventory ingest не является публичным admin API.

`POST /agent/re-enrolments` создаёт 30-минутный запрос восстановления по SMBIOS UUID и возвращает одноразовый claim token. Публичный ответ не сообщает, найдено ли устройство. Installer проверяет состояние через `GET /agent/re-enrolments/{id}` с этим token только в памяти. `ADMIN` видит запросы своей организации через `GET /admin/agent-re-enrolments` и может подтвердить или отклонить их. Подтверждение атомарно отзывает прежний активный credential endpoint и создаёт новый; plaintext token на сервере не хранится. Неизвестный UUID нельзя подтвердить, а чужая организация получает `404`.

`GET /admin/incidents/{incident_id}` возвращает endpoint, время создания, тип изменения, тип компонента, evidence и append-only decisions. Этого ответа достаточно для прямой ссылки на карточку инцидента и восстановления экрана после refresh.

`GET /admin/locations/physical-incidents` и `GET /admin/locations/physical-incidents/{incident_id}` объединяют физические расхождения с техническими в UI. Чтение ограничено tenant и исходным кабинетом инцидента, включая VIEWER grants; evidence/detail и ограничения pagination описаны в [контракте функции](../features/registry-and-incident-center.md).

Inventory envelope проходит version-tolerant минимальную проверку (`content` object и обязательный `deviceid` для `GLPI_AGENT`) после сохранения immutable raw evidence. Конкретные source adapters могут расширять этот контракт, не меняя canonical model.

Per-Agent credential проверяется внутри normalization до изменения endpoint, identifiers, snapshot и history, включая повторный raw payload. Привязанный ключ разрешает только своё устройство; организация найденного устройства должна совпадать с организацией ключа. Новое устройство сразу получает организацию ключа. Scoped key не присваивает endpoint без организации или другой школы; существующий активный ключ заменяется через approved re-enrolment. Первая привязка ключа и snapshot сохраняются одной транзакцией, credential блокируется на время проверки/записи. Нарушение scope возвращает `409`; новый отвергнутый raw остаётся `FAILED`, ранее обработанный duplicate не изменяется. Повторная доставка ранее отвергнутого payload правильным Agent запускает нормализацию и diff один раз.

Vision endpoints находятся в существующей admin boundary `/admin/vision/*`. Upload связывает scan с кабинетом школьной иерархии и принимает JPEG/PNG `image`; результат содержит status, counts, comparison, detections с bounding boxes и защищённые URLs изображений. Доступ к scans/images проходит через локационный grant. Legacy rooms без однозначной связи видны только ADMIN.

`POST /admin/assets/import.xlsx` и `/admin/assets/import.pdf` без `apply=true` возвращают read-only предпросмотр всех распознанных позиций (`items`). При подтверждении `apply=true` те же файлы отправляются повторно; multipart-поле `exclude_row` может повторяться и содержит нулевые индексы исключаемых позиций. Только этот второй запрос записывает оставшиеся строки.

Preview также возвращает `scope: {organization_id, organization_name}` и `items.source_row/source_page`. Некорректные строки обычной таблицы и дубликаты возвращают 422 с object `detail` (`code=IMPORT_ROWS_INVALID`, `message`, `errors[{row,page,message}]`, полный `error_count`, максимум 50 подробностей); другие ошибки могут сохранять строковый detail. До исправления неверного файла ничего не записывается. Apply связывает текстовый кабинет с canonical tenant-scoped `room_id`; отсутствие всех колонок локации сохраняет прежнее назначение, а явно пустой кабинет снимает его. Учётные акты остаются приоритетными. [UI flow, повторные запросы и ограничения](../features/rooms-inspection-and-import.md).

Preview и apply используют одну эффективную организацию: отсутствующая колонка означает tenant principal organization, а для глобального bootstrap — `Default Organization`. Явная чужая организация отклоняется с `403`. В `items` возвращаются `organization`, `quantity`, `unit`, `tracking_mode`, `source_quantity`, `accounting_preserved` и `quantity_unverified`. Неподдерживаемые дробные количества и режимы возвращают `422`. После физического акта сохраняются текущие учётные поля; apply блокирует существующие строки активов до завершения транзакции. Подробный контракт импорта — [PDF/Excel/OCR](../operations/pdf-import-ocr.md).

`GET /admin/operations/status` рассчитывает `agents.stale` по `last_seen_at` и `ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS` (24 по умолчанию), без изменения endpoint status. Просроченный `ONLINE` или `REQUIRES_VERIFICATION` учитывается как stale; `OFFLINE` и `IDENTITY_CONFLICT` остаются отдельными категориями. Tenant и location filters применяются до агрегации.

`GET /admin/locations/rooms/{room_id}/inspections` возвращает последние акты доступного кабинета. `POST` на тот же адрес завершает обход атомарно: запрос обязан содержать ровно один результат для каждой текущей позиции кабинета. Для `MISSING` и `DAMAGED` требуется количество от 1 до учётного остатка; для `PRESENT` количество проблемных единиц равно нулю. Исполнитель определяется по аутентифицированной сессии, а результат добавляется в историю актива и кабинета.

Каждая строка `MISSING` или `DAMAGED` автоматически создаёт физический инцидент, связанный с актом, активом и кабинетом. `POST /admin/locations/physical-incidents/{incident_id}/decision` принимает обязательный комментарий и действие `INVESTIGATE`, `MOVE`, `REPAIR`, `WRITE_OFF` или `FALSE_POSITIVE`. Первое оставляет инцидент `UNDER_REVIEW`, остальные закрывают его. Actor берётся из сессии; решения append-only.

Для `MOVE` обязательны `quantity`, `destination_room_id` и `document_number`; при частичном перемещении групповой позиции также нужен `destination_inventory_number`. Для `WRITE_OFF` обязательны `quantity` и `document_number`. Количество не может превышать ни текущий остаток, ни объём инцидента. Частичная операция разрешена только для группового учёта; полное списание переводит карточку в `WRITTEN_OFF` и убирает её из активного кабинета. `GET /admin/locations/physical-incidents/{incident_id}/act.pdf` формирует акт выполненного перемещения или списания.
