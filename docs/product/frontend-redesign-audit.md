# AssetGuard — UX/UI audit and frontend redesign plan

Дата аудита: **25 сентября 2026 года**
Область: browser UI, используемые им admin API, модели и browser E2E.
Ограничение: backend остаётся source of truth; доменная цепочка `Inventory → Evidence → Snapshot → Baseline → Change → Incident → Decision → History` не меняется.

## A. Что было не так

1. Все крупные сценарии находились на одной длинной HTML-странице. Навигация лишь прокручивала документ, поэтому пользователь не понимал, где заканчивается один рабочий процесс и начинается другой.
2. Не было самостоятельного центра технических инцидентов. Проблемы были видны на Dashboard и внутри карточки устройства, но отсутствовал единый рабочий список с фильтрами.
3. Показатели Dashboard выглядели как справочные цифры и не вели к соответствующим данным.
4. Desktop header был переполнен навигацией, входом и административными действиями. При средней ширине он превращался в многострочную панель.
5. Прямые ссылки существовали только для Asset, а кабинет нельзя было открыть и восстановить после refresh через URL.
6. Back/Forward меняли hash, но не переключали интерфейс как настоящую страницу.
7. Названия разделов смешивали предметные сущности: «Имущество и компьютеры», «Кабинеты», «Проверка по фото» и служебную справку без визуальной иерархии.
8. Система статусов уже централизована в JavaScript, но не все экраны используют один и тот же пользовательский словарь.
9. Часть важных действий использует системные `confirm()`/`prompt()`. Для baseline и решения инцидента нужны собственные доступные модальные формы.
10. Browser E2E покрывал много операций одним сценарием, но почти не проверял routing, Back/Forward и отдельный экран инцидентов.

## B. Карта интерфейса до изменений

- Overview/Dashboard;
- структура помещений и карточка кабинета;
- сотрудники и location grants;
- Agent credentials и инструкция установки;
- реестр имущества/endpoint и карточка Asset;
- справка о работе Agent;
- Vision;
- модальные формы импорта, локаций, обхода, физических операций, связи endpoint, редактирования и QR.

Все перечисленные области физически находились в одном документе и одновременно участвовали в layout.

## C. Реально доступные функции

- Dashboard на данных Assets, Endpoints, Changes, Incidents и Operations status;
- поиск, фильтрация, сортировка и редактирование реестра;
- полная карточка Asset/Endpoint с hardware, baseline, diff, incident и history;
- Excel/PDF preview и выборочное подтверждение импорта, Excel/PDF export;
- Organization → Building → Floor → Room, карточка кабинета;
- physical inspection и физические incident decisions;
- named users, sessions, location grants, Agent credentials;
- Vision scan, counts, bounding boxes, baseline и comparison;
- QR и PDF-акты операций.

## D. Карта используемых API

| Область | Основные endpoints |
| --- | --- |
| Session | `/auth/login`, `/auth/me`, `/auth/logout` |
| Registry | `/admin/assets`, `/admin/endpoints`, `/admin/assets/{id}` |
| Evidence | `/admin/snapshots/*`, `/admin/changes`, `/admin/incidents/*`, `/admin/endpoints/{id}/history` |
| Locations | `/admin/locations/tree`, buildings/floors/rooms, room workspace/inspections/physical incidents |
| Import/export | `/admin/assets/import.xlsx`, `/admin/assets/import.pdf`, export/QR/PDF act endpoints |
| Administration | `/admin/users`, `/admin/sessions`, `/admin/agent-credentials`, `/admin/locations/access` |
| Vision | `/admin/vision/rooms`, `/admin/vision/scans`, room baseline and protected images |
| Operations | `/health`, `/health/ready`, `/admin/operations/status` |

Большой backend rewrite не требуется. Новых endpoints не добавлено; detail-response существующего `/admin/incidents/{id}` дополнен endpoint/change metadata, необходимыми для прямой ссылки.

## E. Что перерабатывается

### Этап 1 — реализовано

- постоянный desktop sidebar и компактное адаптивное меню;
- hash routing, который показывает один логический экран;
- Back/Forward и refresh для основных экранов;
- прямые ссылки `#asset=<uuid>` и `#room=<uuid>`;
- самостоятельный Incident Center с status/severity/search фильтрами;
- реальные comparison «Было → Стало» в карточках инцидентов;
- Dashboard из пяти actionable показателей;
- badge открытых инцидентов в навигации;
- безопасный logout с возвратом на понятный экран входа;
- расширенный browser E2E routing/responsive сценарий.

### Этап 2 — выполняется

- выполнено: полноценная incident detail с прямым route `#incident=<uuid>`, evidence, comparison, историей решений и управляемой формой без `prompt()`/`confirm()`;
- выполнено: вкладки карточки устройства «Обзор / Оборудование / Эталон и изменения / Инциденты / История / Технические данные» с deep-link `#asset=<uuid>&tab=<tab>`, Back/Forward, refresh и клавиатурной навигацией;
- выполнено: единый confirmation dialog для technical baseline, revoke Agent credential и revoke location access;
- выполнено: отдельный экран «Импорт и экспорт» поверх существующего безопасного preview workflow, с прямым route `#data-exchange`, отображением файла, блокировкой повторной отправки и понятным статусом операции;
- выполнено для асинхронных deep routes: asset, room и incident показывают loading, сохраняют понятный error state с retry и не выбрасывают пользователя в другой раздел.

### Этап 3

- выполнено: focus trap/restore для собственных dialog, Escape и keyboard regression для QR dialog; остаётся полная ручная accessibility-проверка;
- выполнено: сокращение повторных API запросов при переходах с коротким кэшем и дедупликацией in-flight запросов;
- выполнено: Vision baseline использует единый доступный confirmation dialog вместо системного `confirm()`;
- выполнено: browser regression на 1920×1080, 1366×768, 900 px, 768 px, 390×844 и 360×800 проверяет отсутствие горизонтальной прокрутки, usable mobile navigation и вмещение dialog;
- модерируемый тест с новым оператором школы.

## F. Navigation architecture после этапа 1

```text
Работа
├── Обзор
├── Устройства
├── Импорт и экспорт
├── Инциденты
├── Помещения
└── Проверка по фото

Управление
├── Сотрудники и доступ
├── Подключить Agent
└── Как работает Agent
```

«Проверки/обходы» пока не вынесены в пустой самостоятельный раздел: backend предоставляет их в контексте кабинета, поэтому workflow остаётся в цифровой карточке помещения.

## G. Reusable frontend primitives

- centralized route metadata и route renderer;
- centralized status label/variant mapping;
- reusable status pill;
- reusable comparison «Было → Стало»;
- metric cards, ведущие к отфильтрованным данным;
- общие empty-state, loading skeleton, toast, panel, toolbar и responsive table patterns.

## H. Regression risks

1. Скрытие неактивных route может сломать старые тесты, которые полагались на одновременную видимость всей страницы.
2. Асинхронный hashchange требует ожидания visible state в browser tests.
3. Admin routes нельзя показывать до определения current user; frontend visibility не заменяет backend authorization.
4. Device/room deep link должен открываться только после восстановления сессии и загрузки базовых данных.
5. Mobile menu и desktop sidebar используют один DOM navigation; нельзя дублировать handlers.

## Functional audit — состояние controls

- Все существующие `button`, form submit и navigation links имеют обработчики либо нативное dialog-действие.
- Экспорт/импорт обрабатывают API errors и показывают feedback.
- Create/edit/location/inspection/physical operation формы блокируют или ограничивают повторные destructive действия в критичных местах.
- Новые filters полностью client-side и не создают повторных API запросов.
- Fake controls не добавлены.
- Технический incident workflow больше не использует `prompt()`/`confirm()`; комментарий обязателен, submit блокируется на время API-запроса, ошибка не закрывает dialog.
- Системные `confirm()` и `prompt()` в основных пользовательских workflow не используются.

## Проверка этапа 1

```powershell
node --check frontend/app.js
cd backend
.venv/Scripts/python.exe -m pytest tests/unit tests/integration -q
$env:ASSETGUARD_RUN_BROWSER_E2E='1'
.venv/Scripts/python.exe -m pytest tests/e2e -q
```

Ожидаемый результат: `28 passed` для unit/integration и `2 passed` для browser E2E, включая отдельный direct-link/decision сценарий инцидента (`30 passed` суммарно).
