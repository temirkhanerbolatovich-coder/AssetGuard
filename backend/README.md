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

## Baseline and change detection

`accept_snapshot_as_baseline()` — единственный путь к `ACTIVE` baseline. Normalizer создаёт только candidate snapshot. `detect_changes()` сравнивает active baseline с current snapshot для RAM и storage, записывает evidence и использует stable dedup key; absence в неполной категории не создаёт removal.

### Текущая Windows-лаборатория

Путь данного workspace содержит кириллицу. У установленного Python 3.12 editable-install создаёт `.pth`, который в этой code page не читается. Для текущей машины рабочая среда находится в `C:\AssetGuardDev\backend-venv`, а ASCII junction `C:\AssetGuardWorkspace` указывает на каталог `backend`. Это временное окружение вне Git; проект не требует переименования.

## AssetGuard Vision

`POST /admin/vision/scans` принимает JPEG/PNG и имя помещения, выполняет lazy Grounding DINO inference и сохраняет detections, counts, original/annotated image. `/admin/vision/rooms/*` предоставляет историю и explicit baseline. Модель загружается только при первом Vision scan, поэтому основной inventory API запускается независимо от inference.

## Ограничения текущего этапа

- Нет подтверждённого direct endpoint нативного протокола GLPI Agent: используется explicit bridge.
- Vision не поддерживает RTSP, quality gate, multi-frame aggregation и автоматический `ANOMALY`.
- Иерархия Institution/Building/Floor не реализована; Vision room задаётся уникальным именем.
- Deployment acceptance на целевом сервере ещё не выполнен.

Эти границы предотвращают ситуацию, когда inventory принимается без неизменяемого RawInventory, payload limit и audit trail.
