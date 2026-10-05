# AssetGuard — матрица доступа `/admin`

Дата проверки: 5 октября 2026 года. Матрица покрывает **63 protected operations** на 56 уникальных путях.

`GET /admin/notifications` — только ADMIN, граница организации, пагинация и фильтр состояния. Возвращаются только метаданные доставки и проверенная внутренняя ссылка: без текста сообщения, получателя, message id, event key и секретов. Администратор платформы видит все организации; администратор школы — только свою. Неизвестная ошибка заменяется `UNKNOWN_ERROR`. Чтение не запускает отправку или повтор.

## Роли и location grants

HTTP dependency `require_admin` допускает только роль `ADMIN`. Dependency `require_viewer` допускает `ADMIN`, `VIEWER`, `LOCATION_MANAGER` и `INVENTORY_CLERK`.

| Уровень route | `ADMIN` | `VIEWER` | `LOCATION_MANAGER` | `INVENTORY_CLERK` | Без token |
| --- | --- | --- | --- | --- | --- |
| Admin | allow | deny | deny | deny | deny |
| Viewer | allow | allow | allow | allow | deny |

Route-level допуск не отменяет resource scope. Для не-`ADMIN` ролей grant `VIEWER` даёт чтение, а grant `EDITOR` — чтение и запись в назначенных room/floor/building. Недоступный room, foreign tenant или UUID возвращает `404`, чтобы не раскрывать существование ресурса.

Bootstrap/shared credential остаётся отдельным platform bootstrap механизмом и не участвует в tenant-isolation tests.

## Реестр и технические события

| Операция | Route-level | Resource scope |
| --- | --- | --- |
| `GET /admin/assets`; exports | Viewer | tenant + granted locations |
| `GET /admin/assets/{id}`; QR | Viewer | tenant + granted location |
| `POST /admin/assets`; `PATCH /admin/assets/{id}` | Viewer | write requires `ADMIN` or `EDITOR` grant |
| `POST /admin/assets/import.xlsx`; `import.pdf` | Admin | tenant |
| `GET /admin/endpoints`; `GET /admin/endpoints/{id}` | Viewer | tenant + granted locations |
| `POST /admin/endpoints/{endpoint}/asset/{asset}` | Admin | tenant |
| `GET /admin/inventories`; `GET /admin/inventories/{id}` | Viewer | tenant + granted locations |
| `GET /admin/operations/status` | Viewer | tenant + granted locations |
| Snapshot, baseline, change, incident and history reads | Viewer | tenant + granted locations |
| Baseline acceptance and incident decisions | Admin | tenant |
| `POST /admin/maintenance/evaluate-endpoints` | Admin | platform operation |

## Помещения, обходы и Vision

| Операция | Route-level | Resource scope |
| --- | --- | --- |
| Location tree, room report, inspections and workspace reads | Viewer | tenant + granted locations |
| Room inspection and physical-incident decision | Viewer | write requires `ADMIN` or `EDITOR` grant |
| Physical-incident list/detail (`GET /admin/locations/physical-incidents[/id]`) | Viewer | tenant + granted original incident location; detail includes inspection evidence |
| Physical-incident act PDF | Viewer | tenant + granted location |
| Create building/floor/room; update room | Admin | tenant |
| Vision room, scan, image and baseline reads | Viewer | tenant + granted locations |
| Vision scan upload and baseline update | Admin | tenant |

## Управление доступом и устройствами

| Операция | Route-level | Resource scope |
| --- | --- | --- |
| `GET/POST/PATCH /admin/users` | Admin | tenant |
| `GET/DELETE /admin/sessions` | Admin | tenant |
| Agent credential list/create/revoke | Admin | tenant |
| Agent re-enrolment list/approve/reject | Admin | tenant; чужой или неподтверждённый endpoint скрыт через `404` |
| Location access list/create/delete | Admin | tenant |
| `GET /admin/locations/organizations` | Admin | tenant |

## Автоматическое доказательство

`tests/unit/test_admin_route_contract.py` хранит исполняемый реестр всех 62 method/path operations. Тест падает при добавлении, удалении или переносе операции между Admin и Viewer level. Там же автоматизирована allow/deny-матрица для всех четырёх ролей и запроса без token.

`tests/integration/test_tenant_isolation.py` создаёт две организации с asset, endpoint, raw inventory, snapshot, baseline, change, incident, history, Vision room, user, session, Agent credential и re-enrolment request. Он доказывает фильтрацию списков, `404` для foreign UUID и запрет изменения foreign resources.

`tests/integration/test_location_scoped_resources.py` проверяет grants `VIEWER`/`EDITOR`, фильтрацию exports/Vision и `404` для неразрешённого помещения, включая endpoint detail, report, workspace, inspections и Vision baseline.

Остающаяся ручная приёмка: повторить tenant/location isolation на двух реальных пилотных организациях перед расширением deployment.
