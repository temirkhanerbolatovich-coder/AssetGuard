# AssetGuard Vision — анализ интеграции до разработки

## Текущее состояние AssetGuard

| Область | Наблюдение | Вывод для Vision |
| --- | --- | --- |
| Backend | FastAPI modular monolith; routers `/internal/inventories` и `/admin/*` | Vision API добавляется отдельным router/module, не меняя Agent ingestion. |
| Данные активов | Есть `OrganizationRecord`, `AssetRecord`, поле `AssetRecord.room` строкой | Полноценной модели `Building`/`Floor`/`Room` пока нет; для Vision нужна нормализованная room hierarchy, а не повторное использование строки. |
| Devices | `ManagedEndpointRecord` связан с Asset | Digital inventory room можно агрегировать по assets, но связывание detections ↔ endpoints запрещено в MVP. |
| Evidence workflow | Есть snapshot → explicit baseline → change → incident → history для hardware endpoint | Vision нужен отдельный room-level workflow. Повторно использовать hardware baseline нельзя: единицы, owner и правила подтверждения отличаются. |
| UI | Одна HTML/JS dashboard страница с Assets и endpoint detail | Vision добавляется отдельным разделом/room page, сохраняя текущие карточки и token-auth UI. |

## Минимальная целевая граница

`Dashboard upload → Vision Service → AssetGuard Vision API → PostgreSQL/object storage → Dashboard`.

Vision Service владеет inference и annotated image generation. AssetGuard владеет room hierarchy, access control, scan/detection persistence, baseline/count comparison, warning/anomaly state и display. Для MVP разумен отдельный service process/container с HTTP contract; основной backend не импортирует ML runtime и не зависит от его доступности.

## Предлагаемая очередность, когда будет дано разрешение

1. Создать `Institution`, `Building`, `Floor`, `Room` и явную миграцию данных из `AssetRecord.room`; не удалять старое поле до миграции.
2. Зафиксировать Vision Service API contract и storage abstraction для uploaded/annotated images; добавить size/type limits.
3. Поднять отдельный Vision Service с mock detector и contract tests. Только затем подключать Grounding DINO и его model lifecycle.
4. Добавить `VisionScan`, immutable detections, baseline items и count-comparison (`WARNING` first).
5. Реализовать upload + room page + annotated-image display + history.
6. Добавить operator confirmation/repeated-scan rule для `ANOMALY`, threshold/configuration и error/observability path.

## Необходимые решения перед реализацией

- Где хранятся uploaded/annotated images: локальный volume для demo или S3-compatible object storage.
- Какая среда запуска модели: CPU demo или GPU; Grounding DINO runtime/веса нельзя включать в базовый backend image без отдельного решения.
- Кто создаёт и редактирует hierarchy Institution/Building/Floor/Room и каким образом первоначально мигрировать строковые room значения.
- Каким правилом WARNING превращается в ANOMALY: количество последовательных scans, период либо явное решение оператора.
- Политика retention и права доступа к фотографиям помещений.

## Риски, учтённые в ТЗ

Count mismatch не доказывает пропажу: плохой ракурс, освещение и перекрытие создают ложные срабатывания. Поэтому confidence threshold, immutable scan history, initial WARNING и ручное/повторное подтверждение являются обязательными, а не UI-деталями.
