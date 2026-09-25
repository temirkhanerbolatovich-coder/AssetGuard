# AssetGuard — матрица доступа `/admin`

Дата проверки: 25 сентября 2026 года.

## Обозначения

- **A** — именованный `ADMIN` организации: допускается только к своей организации.
- **V** — пользователь с grant `VIEWER` на помещение: читает только разрешённые помещения.
- **E** — пользователь с grant `EDITOR` на помещение: имеет права V и может выполнить указанное действие в разрешённом помещении.
- **F** — ресурс другой организации. Для именованного пользователя ответ всегда `404`, чтобы не раскрывать существование ресурса.
- Bootstrap/shared credential остаётся платформенным механизмом для первоначальной настройки; он не является tenant-scoped ролью и не используется для проверки F.

## Реестр и технические события

| Маршрут | A | V | E | F |
| --- | --- | --- | --- | --- |
| `GET /admin/assets` | own tenant | allowed rooms | allowed rooms | filtered |
| `GET /admin/assets/export.xlsx`, `export.pdf` | own tenant | allowed rooms | allowed rooms | filtered |
| `GET /admin/assets/{id}`, `{id}/qr.svg` | own asset | allowed room | allowed room | 404 |
| `POST /admin/assets`, `PATCH /admin/assets/{id}` | own tenant | deny | only permitted room on update | 404 |
| `POST /admin/assets/import.xlsx`, `import.pdf` | own tenant | deny | deny | 403/404 |
| `GET /admin/endpoints` | own tenant | allowed rooms | allowed rooms | filtered |
| `GET /admin/endpoints/{id}` | own endpoint | allowed room | allowed room | 404 |
| `POST /admin/endpoints/{endpoint}/asset/{asset}` | own tenant | deny | deny | 404 |
| `GET /admin/inventories`, `/inventories/{id}` | own tenant | allowed room | allowed room | filtered/404 |
| `GET /admin/endpoints/{id}/snapshots`, `baseline`, `history` | own endpoint | allowed room | allowed room | 404 |
| `GET /admin/snapshots/{id}` | own snapshot | allowed room | allowed room | 404 |
| `POST /admin/snapshots/{id}/baseline` | own snapshot | deny | deny | 404 |
| `GET /admin/changes`, `/changes/{id}` | own tenant | allowed rooms | allowed rooms | filtered/404 |
| `GET /admin/incidents`, `/incidents/{id}` | own tenant | allowed rooms | allowed rooms | filtered/404 |
| `POST /admin/incidents/{id}/decision`, `resolve` | own incident | deny | deny | 404 |
| `POST /admin/maintenance/evaluate-endpoints` | own platform scope | deny | deny | deny |

## Помещения, обходы и Vision

| Маршрут | A | V | E | F |
| --- | --- | --- | --- | --- |
| `GET /admin/locations/tree` | own tenant | allowed rooms | allowed rooms | filtered |
| `GET /admin/locations/rooms/{id}/report`, `inspections`, `workspace` | own room | allowed room | allowed room | 404 |
| `POST /admin/locations/rooms/{id}/inspections` | own room | deny | allowed room | 404 |
| `POST /admin/locations/physical-incidents/{id}/decision` | own incident | deny | allowed room | 404 |
| `GET /admin/locations/physical-incidents/{id}/act.pdf` | own incident | allowed room | allowed room | 404 |
| `POST /admin/locations/buildings`, `floors`, `rooms`; `PATCH /rooms/{id}` | own tenant | deny | deny | 404 |
| `GET /admin/vision/rooms`, `rooms/{id}/scans`, `baseline` | own tenant/room | allowed room | allowed room | filtered/404 |
| `GET /admin/vision/scans/{id}`, `/image` | own scan | allowed room | allowed room | 404 |
| `POST /admin/vision/scans`, `rooms/{id}/baseline` | own tenant/room | deny | deny | 404 |

## Управление доступом и устройствами

| Маршрут | A | V | E | F |
| --- | --- | --- | --- | --- |
| `GET/POST/PATCH /admin/users` | own tenant | deny | deny | list filtered; item 404 |
| `GET/DELETE /admin/sessions` | own tenant | deny | deny | list filtered; item 404 |
| `GET/POST /admin/agent-credentials`, `POST /{id}/revoke` | own tenant | deny | deny | list filtered; item 404/403 |
| `GET/POST/DELETE /admin/locations/access` | own tenant | deny | deny | list filtered; item 404 |
| `GET /admin/locations/organizations` | own tenant | deny | deny | filtered |

## Автоматическое доказательство

`tests/integration/test_tenant_isolation.py` создаёт отдельную организацию с asset, endpoint, raw inventory, snapshot, baseline, change, incident, history и Vision room. Он доказывает `404` для foreign UUID и для изменения чужого baseline/incident.

`tests/integration/test_location_scoped_resources.py` проверяет фильтрацию exports/Vision и `404` для ресурса в неразрешённом помещении, включая endpoint detail. Полный набор backend-тестов на момент этой записи: **30 passed**.

Открытая работа для полного P0: расширить эти сценарии параметризованной проверкой каждого маршрута из таблицы с A/V/E/F и добавить реальные две школы в приемочное тестирование.
