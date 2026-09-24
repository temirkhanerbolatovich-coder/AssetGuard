# AssetGuard backend

Backend реализован как Python 3.12 modular monolith на FastAPI. Он объединяет защищённый inventory gateway, нормализацию hardware, baseline/change/incident workflow, административный API и изолированный AssetGuard Vision module. Gateway сохраняет payload в immutable `RawInventory` до любой нормализации.

## Локальный запуск

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev,vision]"
python -m uvicorn assetguard.app:app --reload
```

Проверка: `GET http://127.0.0.1:8000/health`.

## Internal inventory gateway

`POST /internal/inventories` — это временный AssetGuard-internal контракт для адаптеров и fixtures, а не подтверждённый endpoint протокола GLPI Agent. Он требует следующие headers:

- `X-AssetGuard-Ingest-Token` — shared secret из local environment;
- `X-AssetGuard-Idempotency-Key` — уникальный ключ повторной доставки;
- `X-AssetGuard-Source` — имя источника;
- `X-AssetGuard-Inventory-Type` — `FULL`, `PARTIAL` или `UNKNOWN`.

Endpoint принимает JSON object до 2 MiB по умолчанию, сохраняет SHA-256 и возвращает `202` для новой записи, `200` для повторной доставки того же payload и `409` при повторном ключе с иным payload. После сохранения evidence синхронный application workflow создаёт snapshot и выполняет безопасное сравнение с baseline; сам ingest никогда автоматически не меняет baseline.

## Native GLPI Agent transport

`POST /glpi-agent` реализует наблюдаемый GLPI Agent 1.19 legacy XML flow: authenticated `PROLOG` → `<RESPONSE>SEND</RESPONSE>` → `INVENTORY`. Агент использует HTTP Basic user `assetguard`, а password равен rotating `ASSETGUARD_INVENTORY_SHARED_SECRET`. Для endpoint обязателен agent option `no-compression = 1`; вне loopback используется только HTTPS с нормальной проверкой сертификата.

`DirectGlpiAgentAdapter` сохраняет исходный XML и его SHA-256 внутри immutable JSONB evidence, преобразует секции в canonical GLPI-shaped envelope и запускает тот же snapshot/change/incident workflow. Inventory считается `FULL` только при наличии списков `MEMORIES` и `STORAGES`; иначе используется безопасный `PARTIAL`, который не создаёт removals по отсутствующим категориям.

## Baseline and change detection

`accept_snapshot_as_baseline()` — единственный путь к `ACTIVE` baseline. Normalizer создаёт только candidate snapshot. `detect_changes()` сравнивает active baseline с current snapshot для RAM и storage, записывает evidence и использует stable dedup key; absence в неполной категории не создаёт removal.

### Текущая Windows-лаборатория

Путь данного workspace содержит кириллицу. Установленный Python 3.12 editable-install создаёт `.pth`, который в этой code page не читается. Для текущей машины рабочая среда находится в `C:\AssetGuardDev\backend-venv`, а ASCII junction `C:\AssetGuardWorkspace` указывает на каталог `backend`. `scripts/windows/start-demo.ps1` запускает Python с `-S` и явно подключает исходники и `site-packages`, поэтому миграции и API стартуют без чтения проблемного `.pth`. Это локальная особенность окружения, не часть поставки приложения.

## AssetGuard Vision

`POST /admin/vision/scans` принимает JPEG/PNG и кабинет из структуры школы, выполняет lazy Grounding DINO inference и сохраняет detections, counts, original/annotated image. История и изображения проверяются по tenant и назначенным кабинетам; старые проверки без однозначной связи с кабинетом доступны только администраторам. Модель загружается только при первом Vision scan, поэтому основной inventory API запускается независимо от inference.

## Импорт PDF и OCR

PDF с текстовым слоем разбирается постранично. Для сканов доступен бесплатный Tesseract OCR (языки rus/kaz/eng); распознаются только строки, похожие на отдельные позиции ведомости. Перед применением UI показывает все позиции по 25 строк на странице, поиск, локацию, ожидаемое создание/обновление и ориентировочную уверенность OCR. Строки можно исключить, а сервер повторно разбирает тот же файл и применяет только выбранные позиции после явного подтверждения. Пустые бланки и сводные поля без отдельных позиций не создают фиктивные активы.

Production Docker image включает Tesseract и языковые пакеты. Для локального запуска установите Tesseract отдельно и добавьте его в PATH либо укажите полный путь в `ASSETGUARD_TESSERACT_CMD`; если модели языков размещены отдельно, задайте их каталог через `ASSETGUARD_TESSDATA_DIR`. На Windows также задайте ASCII-путь к доступной на запись временной папке в `ASSETGUARD_OCR_TEMP_DIR`; это избегает ошибок системной кодировки в путях с кириллицей. Если OCR недоступен или в скане не найдены надёжные отдельные позиции, импорт вернёт понятную ошибку, а не создаст фиктивные активы. Лимиты PDF: 10 MiB; OCR-скан — не более 30 страниц.

## Ограничения текущего этапа

- Native endpoint подтверждён локальным end-to-end запуском неизменённого GLPI Agent 1.19; production TLS/DNS acceptance ещё не выполнен.
- Vision не поддерживает RTSP, quality gate, multi-frame aggregation и автоматический `ANOMALY`.
- Иерархия корпус/этаж/кабинет и точечная привязка Vision к кабинету реализованы; импорт не извлекает из PDF кабинет без явных данных и пока не поддерживает RTSP, много кадров и подтверждение аномалий.
- Deployment acceptance на целевом сервере ещё не выполнен.

Эти границы предотвращают ситуацию, когда inventory принимается без неизменяемого RawInventory, payload limit и audit trail.
