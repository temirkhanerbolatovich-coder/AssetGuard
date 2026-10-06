# Полный реестр HTTP API AssetGuard

Сверка: 2026-10-06, source checkout `dca5a86`. Реестр получен из `app.openapi()` и сравнен с `ADMIN_OPERATIONS`/`VIEWER_OPERATIONS` в `backend/tests/unit/test_admin_route_contract.py`.

**73 HTTP operations / 66 путей; 64 admin operations / 57 путей, 29 ADMIN-only и 35 Viewer-level.** Static frontend, `/docs`, `/openapi.json` и неявные HEAD/OPTIONS не входят в этот счётчик.

Последующее локальное исправление свежести Agent добавляет поля ответа, сохраняя весь реестр method/path и доступ: [контракт `connection_status`](README.md), [регрессионная проверка](../../outputs/assetguard-agent-status-fixes-2026-10-06/report.md).

Viewer-level допускает четыре роли, но resource scope и ADMIN/EDITOR write checks обязательны дополнительно. Название роли не заменяет grant. [Полная scope matrix](../security/admin-route-access-matrix.md), [body/error contracts](README.md). Public create re-enrolment не подтверждает известность UUID; polling требует claim token. `/auth/logout` отзывает именованную сессию, bootstrap credential не становится named session.

| Метод | Путь | Route-level доступ | OpenAPI operation |
| --- | --- | --- | --- |
| `GET` | `/admin/agent-credentials` | ADMIN | Agent Credentials |
| `POST` | `/admin/agent-credentials` | ADMIN | Create Agent Credential |
| `POST` | `/admin/agent-credentials/{credential_id}/revoke` | ADMIN | Revoke Agent Credential |
| `GET` | `/admin/agent-re-enrolments` | ADMIN | Agent Reenrolments |
| `POST` | `/admin/agent-re-enrolments/{request_id}/approve` | ADMIN | Approve Agent Reenrolment |
| `POST` | `/admin/agent-re-enrolments/{request_id}/reject` | ADMIN | Reject Agent Reenrolment |
| `GET` | `/admin/assets` | Viewer-level + resource scope | List Assets |
| `POST` | `/admin/assets` | Viewer-level + resource scope | Create Asset |
| `GET` | `/admin/assets/export.pdf` | Viewer-level + resource scope | Export Assets Pdf |
| `GET` | `/admin/assets/export.xlsx` | Viewer-level + resource scope | Export Assets Xlsx |
| `POST` | `/admin/assets/import.pdf` | ADMIN | Import Assets Pdf |
| `POST` | `/admin/assets/import.xlsx` | ADMIN | Import Assets Xlsx |
| `GET` | `/admin/assets/{asset_id}` | Viewer-level + resource scope | Asset Detail |
| `PATCH` | `/admin/assets/{asset_id}` | Viewer-level + resource scope | Update Asset |
| `GET` | `/admin/assets/{asset_id}/qr.svg` | Viewer-level + resource scope | Asset Qr Svg |
| `GET` | `/admin/changes` | Viewer-level + resource scope | Changes |
| `GET` | `/admin/changes/{change_id}` | Viewer-level + resource scope | Change |
| `GET` | `/admin/endpoints` | Viewer-level + resource scope | List Endpoints |
| `GET` | `/admin/endpoints/{endpoint_id}` | Viewer-level + resource scope | Endpoint Detail |
| `POST` | `/admin/endpoints/{endpoint_id}/asset/{asset_id}` | ADMIN | Link Endpoint |
| `GET` | `/admin/endpoints/{endpoint_id}/baseline` | Viewer-level + resource scope | Baseline |
| `GET` | `/admin/endpoints/{endpoint_id}/history` | Viewer-level + resource scope | History |
| `GET` | `/admin/endpoints/{endpoint_id}/snapshots` | Viewer-level + resource scope | Snapshots |
| `GET` | `/admin/incidents` | Viewer-level + resource scope | Incidents |
| `GET` | `/admin/incidents/{incident_id}` | Viewer-level + resource scope | Incident |
| `POST` | `/admin/incidents/{incident_id}/decision` | ADMIN | Decision |
| `POST` | `/admin/incidents/{incident_id}/resolve` | ADMIN | Resolve |
| `GET` | `/admin/inventories` | Viewer-level + resource scope | List Inventories |
| `GET` | `/admin/inventories/{inventory_id}` | Viewer-level + resource scope | Inventory Detail |
| `GET` | `/admin/locations/access` | ADMIN | List Access |
| `POST` | `/admin/locations/access` | ADMIN | Grant Access |
| `DELETE` | `/admin/locations/access/{access_id}` | ADMIN | Revoke Access |
| `POST` | `/admin/locations/buildings` | ADMIN | Create Building |
| `POST` | `/admin/locations/buildings/{building_id}/floors` | ADMIN | Create Floor |
| `POST` | `/admin/locations/floors/{floor_id}/rooms` | ADMIN | Create Room |
| `GET` | `/admin/locations/organizations` | ADMIN | Organizations |
| `GET` | `/admin/locations/physical-incidents` | Viewer-level + resource scope | List Physical Incidents |
| `GET` | `/admin/locations/physical-incidents/{incident_id}` | Viewer-level + resource scope | Physical Incident Detail |
| `GET` | `/admin/locations/physical-incidents/{incident_id}/act.pdf` | Viewer-level + resource scope | Physical Incident Act |
| `POST` | `/admin/locations/physical-incidents/{incident_id}/decision` | Viewer-level + resource scope | Decide Physical Incident |
| `PATCH` | `/admin/locations/rooms/{room_id}` | ADMIN | Update Room |
| `GET` | `/admin/locations/rooms/{room_id}/inspections` | Viewer-level + resource scope | Room Inspections |
| `POST` | `/admin/locations/rooms/{room_id}/inspections` | Viewer-level + resource scope | Create Room Inspection |
| `GET` | `/admin/locations/rooms/{room_id}/qr.svg` | Viewer-level + resource scope | Room Qr Svg |
| `GET` | `/admin/locations/rooms/{room_id}/report` | Viewer-level + resource scope | Room Report |
| `GET` | `/admin/locations/rooms/{room_id}/workspace` | Viewer-level + resource scope | Room Workspace |
| `GET` | `/admin/locations/tree` | Viewer-level + resource scope | Location Tree |
| `POST` | `/admin/maintenance/evaluate-endpoints` | ADMIN | Evaluate Endpoints |
| `GET` | `/admin/notifications` | ADMIN | Notifications |
| `GET` | `/admin/operations/status` | Viewer-level + resource scope | Operations Status |
| `GET` | `/admin/sessions` | ADMIN | Sessions |
| `DELETE` | `/admin/sessions/{session_id}` | ADMIN | Revoke Session |
| `GET` | `/admin/snapshots/{snapshot_id}` | Viewer-level + resource scope | Snapshot |
| `POST` | `/admin/snapshots/{snapshot_id}/baseline` | ADMIN | Accept Baseline |
| `GET` | `/admin/users` | ADMIN | Users |
| `POST` | `/admin/users` | ADMIN | Create User |
| `PATCH` | `/admin/users/{user_id}` | ADMIN | Update User |
| `GET` | `/admin/vision/rooms` | Viewer-level + resource scope | Rooms |
| `GET` | `/admin/vision/rooms/{room_id}/baseline` | Viewer-level + resource scope | Get Baseline |
| `POST` | `/admin/vision/rooms/{room_id}/baseline` | ADMIN | Save Baseline |
| `GET` | `/admin/vision/rooms/{room_id}/scans` | Viewer-level + resource scope | Room Scans |
| `POST` | `/admin/vision/scans` | ADMIN | Upload Scan |
| `GET` | `/admin/vision/scans/{scan_id}` | Viewer-level + resource scope | Scan Detail |
| `GET` | `/admin/vision/scans/{scan_id}/image` | Viewer-level + resource scope | Scan Image |
| `POST` | `/agent/re-enrolments` | Public, validated request body | Request Agent Reenrolment |
| `GET` | `/agent/re-enrolments/{request_id}` | Claim token in X-AssetGuard-Reenrolment-Token | Agent Reenrolment Status |
| `POST` | `/auth/login` | Public | Login |
| `POST` | `/auth/logout` | Valid named session; missing/revoked/shared token → 401 | Logout |
| `GET` | `/auth/me` | Viewer-level named session or configured shared admin/viewer token | Current User |
| `POST` | `/glpi-agent` | HTTP Basic / Agent credential | Receive Glpi Agent |
| `GET` | `/health` | Public | Health |
| `GET` | `/health/ready` | Public | Readiness |
| `POST` | `/internal/inventories` | Ingest shared secret | Receive Inventory |

`GET /glpi-agent` отсутствует; запрос браузером получает 404. Для XML `POST /glpi-agent` без Basic credentials ожидается 401. Public liveness/readiness возвращают только process/DB state; API version `0.1.0` не является Git release identifier.

Для проверки соответствия после изменения маршрутов из `backend`: `.\.venv\Scripts\python.exe -m pytest -q tests/unit/test_admin_route_contract.py`. Затем сравните method/path и policy с OpenAPI и обновите этот реестр. Schema request/response доступна через `/openapi.json`; role/scope guards остаются источником авторизации.
