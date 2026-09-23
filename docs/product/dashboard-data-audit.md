# Dashboard data audit

Дата проверки: 2026-09-23. Источники: GLPI Agent 1.19, сохранённые raw inventories, SQLAlchemy models, REST handlers и browser Dashboard.

## Фактический путь данных

`GLPI Agent → native XML / JSON bridge → RawInventory JSONB → normalized snapshots → admin API → Dashboard`

Raw evidence остаётся неизменяемым. Для интерфейса используются нормализованные компоненты, а системные секции последней успешной инвентаризации читаются из сохранённого payload. Частичный inventory не стирает ранее наблюдавшиеся сведения: UI выбирает последние достоверные данные отдельно по каждой категории.

| Категория Agent | Хранение | API после UX-доработки | Dashboard |
| --- | --- | --- | --- |
| Hardware / hostname / UUID | Raw JSONB + endpoint identifiers | Asset detail, endpoint summary | Общая карточка и идентификаторы |
| BIOS / system manufacturer / model / serial | Raw JSONB + identifiers | `system.bios` | Секция Windows и BIOS |
| Operating system | Raw JSONB | `system.operating_system` | ОС, версия, build/kernel, architecture |
| CPU | Component observation + raw data | Current hardware | Модель, cores, threads, speed, manufacturer |
| RAM | Component observation + raw data | Current/baseline hardware | Общий объём, модули, slot, manufacturer, serial, part number, speed/type |
| Physical storage | Component observation + raw data | Current/baseline hardware | Model, serial, size, type, interface, firmware |
| Drives/partitions | Raw JSONB | `system.drives` | Letter/label, filesystem, total/free, system drive |
| GPU | Component observation + raw data | Current hardware | Model, memory, resolution, chipset, PCI slot |
| Motherboard | Component observation + identifiers | Current hardware | Manufacturer, model, serial/part number |
| Controllers | Raw JSONB | `system.controllers` | Сводка с progressive disclosure |
| Network adapters | Component observation, если секция пришла | Current hardware | MAC/IP/status/speed при наличии данных |
| Monitors | Component observation | Current hardware | Model/manufacturer/serial |
| Network quality (ping/jitter/loss/upload/download) | Не собирается текущим profile | Не выдаётся | Не имитируется |
| Asset location | Asset + Organization | Asset/endpoint lists and detail | Организация, кабинет, фильтр и сводка |
| Baseline / changes / incidents / history | Нормализованные таблицы | Existing workflow API | Читаемое «Было → Стало», решения и timeline |
| Vision | Room/scan/baseline tables + images | Existing Vision API | Единый сценарий кабинет → фото → сравнение → подтверждение |

## UX-решения

- Dashboard сначала отвечает на вопрос «что требует внимания», затем раскрывает детали.
- Реестр объединяет связанные активы, активы без Agent и непривязанные endpoints без дублирования.
- Backend statuses переводятся в единые пользовательские состояния: «В норме», «Требует внимания», «Обнаружено расхождение», «Не в сети», «Не проверено».
- Raw JSON пользователю не показывается; evidence преобразуется в сравнение предыдущего и текущего состояния.
- Baseline изменяется только после явного подтверждения с предупреждением.
- Большие технические списки, например контроллеры, свёрнуты по умолчанию.
