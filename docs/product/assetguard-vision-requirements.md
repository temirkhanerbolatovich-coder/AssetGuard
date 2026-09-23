# AssetGuard Vision — сохранённые требования

Источник: ТЗ пользователя от 2026-09-23. Статус: **демонстрационный vertical slice реализован**.

Реализован согласованный сценарий `Upload → Detection → Bounding Boxes → Object count → Baseline → повторный Scan → Comparison → WARNING`. Иерархия Institution/Building/Floor, RTSP, `ANOMALY`, связь detection с endpoint и production object storage намеренно оставлены за пределами сегодняшнего MVP.

## Цель и границы

Vision — второй независимый источник инвентарных данных: фотографии помещений → object detection → AssetGuard API → единый Dashboard. Windows Agent продолжает отвечать за цифровую инвентаризацию компьютеров. Vision Service изолирован; его отказ не должен влиять на Agent, основной API, базу и существующий Dashboard.

MVP: загрузка фотографии через Dashboard, обработка 2–10 секунд, детекции с классом/confidence/bounding box, annotated image, история и сравнение с эталоном помещения. RTSP, поток 25–30 FPS, face recognition, tracking, обучение модели, мобильное приложение, автоматическое сопоставление bounding box с PC-ID и сложные уведомления исключены из MVP.

## Computer Vision и результат

- Предпочтительная open-source основа: Grounding DINO; zero-shot/open-vocabulary detection.
- Список классов конфигурируемый, а не зашитый в модель: минимум `monitor`, `computer`, `printer`, `projector`, `television`, `keyboard`, `laptop`, `chair`, `table`.
- Каждая detection: `class`, `confidence`, `bbox {x1,y1,x2,y2}`.
- У каждой проверки: `room_id`, timestamp, набор detections, summary counts, original и annotated image.
- Настраиваемый `VISION_CONFIDENCE_THRESHOLD` (пример 0.35); детекции ниже порога не участвуют в сравнении.

## Baseline, статусы, история

- Для помещения хранится вручную созданный либо подтверждённый baseline `{class_name: expected_count}`.
- При новом scan сравниваются expected/detected counts.
- Статусы: `NOT_CHECKED`, `OK`, `WARNING`, `ANOMALY`.
- Первое расхождение всегда `WARNING`; это не равнозначно missing asset. `ANOMALY` появляется только после повторных проверок или решения оператора.
- Нужна история Vision Scan с количеством по классам, статусом и аномалиями.

## UI и интеграция

- Новый раздел: Institution → Building → Floor → Room.
- Карточка room: Physical inventory, Digital inventory от существующих Agents, последнее annotated image, history.
- Данные Vision и Windows Agent показываются рядом, но в MVP не связывают конкретный физический объект с конкретным endpoint.
- Нужны действия: upload/Run scan, View image, History, Save/Update baseline.

## API и persistence

- Минимум: upload/detect для `room_id`; получение scans (room и scan); create/get baseline.
- Не создавать параллельный API standard: маршруты должны жить в существующем AssetGuard backend/API boundary.
- Целевые сущности: `VisionScan`, `VisionDetection`, `InventoryBaseline`, `BaselineItem`; хранить путь к source/processed image, статус, timestamps, counts/detections/bounding boxes.
- Будущее: Camera с `camera_id`, `room_id`, `rtsp_url`, `scan_interval`, `enabled`; периодические кадры 08:00/12:00/16:00/20:00.

## Privacy, fault tolerance, observability

- Не распознавать лица, людей и биометрические данные; человек рассматривается максимум как временное перекрытие объекта.
- Логировать start, image received, model loaded, detections, completion, API response, error.
- Ошибка Vision Service не должна падать основной backend.

## MVP success demonstration

Room 305: photo 1 показывает 12 monitors, 12 computers и 1 printer → Save baseline. На photo 2 — 11 monitors при остальных неизменных counts → Dashboard показывает inventory change (expected 12, detected 11, difference −1), initial WARNING и history.

В репозитории находится воспроизводимая demo-пара `demo/vision/room-305-baseline.png` и `demo/vision/room-305-warning.png`. Вторая фотография не содержит принтер; реальный detector фиксирует `printer: 1 → 0`, а Dashboard показывает `WARNING`. Количество других объектов зависит от zero-shot модели и качества кадра, поэтому demo доказывает workflow, а не метрическую точность production-модели.
