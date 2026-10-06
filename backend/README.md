# AssetGuard backend

> **Сверено 2026-10-07.** Текущий статус и границы проверки: [checklist](../docs/product/current-project-checklist.md), [аудит](../docs/quality/project-audit-2026-10-06.md). Датированные результаты отдельных этапов сохранены с исходными датами.

Backend реализован как Python 3.12 modular monolith на FastAPI. Он объединяет защищённый inventory gateway, нормализацию hardware, baseline/change/incident workflow, административный API и изолированный AssetGuard Vision module. Gateway сохраняет payload в immutable `RawInventory` до любой нормализации.

Backend package/API version остаётся `0.1.0`; schema head — `0026_telegram_notifications` (26 migrations). Актуальный application release определяется SHA в [checklist](../docs/product/current-project-checklist.md). OpenAPI содержит 73 operations, из них 64 admin: [route reference](../docs/api/route-reference.md).

## Локальный запуск

Опубликованное в application `7c45435` исправление от 2026-10-06 добавляет отдельный read-only `connection_status` для согласованной свежести Agent в API и кабинете. XML-версия `GLPI-Agent_v1.20` распознаётся как проверенная `1.20` без изменения исходного evidence. [Контракт](../docs/features/agent-administration-and-delivery.md) и [проверка](../outputs/assetguard-agent-status-fixes-2026-10-06/report.md). Миграции и зависимости не добавлены. Публикация и выкладка отражаются в checklist отдельно.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[dev]"
python -m alembic upgrade head
python -m uvicorn assetguard.app:app --reload
```

До команд создайте локальный `.env` из корневой инструкции и запустите PostgreSQL. Проверка процесса: `GET http://127.0.0.1:8000/health`; подключение к БД: `/health/ready`. Для Vision установите `.[dev,vision]` отдельно; для browser tests — `.[dev,e2e]` и Chromium.

## Internal inventory gateway

`POST /internal/inventories` — это временный AssetGuard-internal контракт для адаптеров и fixtures, а не подтверждённый endpoint протокола GLPI Agent. Он требует следующие headers:

- `X-AssetGuard-Ingest-Token` — shared secret из local environment;
- `X-AssetGuard-Idempotency-Key` — уникальный ключ повторной доставки;
- `X-AssetGuard-Source` — имя источника;
- `X-AssetGuard-Inventory-Type` — `FULL`, `PARTIAL` или `UNKNOWN`.

Endpoint принимает JSON object до 2 MiB по умолчанию, сохраняет SHA-256 и возвращает `202` для новой записи, `200` для повторной доставки того же payload и `409` при повторном ключе с иным payload. После сохранения evidence синхронный application workflow создаёт snapshot и выполняет безопасное сравнение с baseline; сам ingest никогда автоматически не меняет baseline.

## Native GLPI Agent transport

`POST /glpi-agent` реализует наблюдаемый GLPI Agent 1.19/1.20 XML flow: authenticated `PROLOG` → `<RESPONSE>SEND</RESPONSE>` → `INVENTORY`. Основной путь использует отдельный HTTP Basic username/secret для каждого компьютера; legacy shared credential остаётся временным fallback до завершения миграции пилотного парка. Для endpoint обязателен agent option `no-compression = 1`; вне loopback используется только HTTPS с нормальной проверкой сертификата.

`DirectGlpiAgentAdapter` сохраняет исходный XML и его SHA-256 внутри immutable JSONB evidence, преобразует секции в canonical GLPI-shaped envelope и запускает тот же snapshot/change/incident workflow. Inventory считается `FULL` только при наличии списков `MEMORIES` и `STORAGES`; иначе используется безопасный `PARTIAL`, который не создаёт removals по отсутствующим категориям.

## Baseline and change detection

`accept_snapshot_as_baseline()` — единственный путь к `ACTIVE` baseline. Normalizer создаёт только candidate snapshot. `detect_changes()` сравнивает active baseline с current snapshot для RAM и storage, записывает evidence и использует stable dedup key; absence в неполной категории не создаёт removal.

### Windows-окружение и путь checkout

Для нового editable install рекомендуется ASCII-путь checkout. Ранее кириллица и системная code page вызывали ошибку чтения `.pth`; обход использовал `C:\AssetGuardDev\backend-venv` и junction `C:\AssetGuardWorkspace` на `backend`. На сверке 2026-10-06 обычный `backend/.venv/Scripts/python.exe` (Python 3.12.3) в текущем checkout успешно импортировал пакет и выполнил полный pytest. `scripts/windows/start-demo.ps1` по-прежнему выбирает старый ASCII fallback, если оба пути существуют, и запускает Python с `-S`, явно добавляя исходники и `site-packages`. Это совместимость с локальным Windows-окружением; наличие fallback нельзя считать обязательным условием запуска.

## AssetGuard Vision

`POST /admin/vision/scans` принимает JPEG/PNG и кабинет из структуры школы, выполняет lazy Grounding DINO inference и сохраняет detections, counts, original/annotated image. История и изображения проверяются по tenant и назначенным кабинетам; старые проверки без однозначной связи с кабинетом доступны только администраторам. Модель загружается только при первом Vision scan, поэтому основной inventory API запускается независимо от inference.

## Импорт PDF и OCR

PDF с текстовым слоем разбирается постранично. Для сканов доступен бесплатный Tesseract OCR (языки rus/kaz/eng); распознаются только строки, похожие на отдельные позиции ведомости. Перед применением UI показывает все позиции по 25 строк на странице, поиск, локацию, ожидаемое создание/обновление и ориентировочную уверенность OCR. Строки можно исключить, а сервер повторно разбирает тот же файл и применяет только выбранные позиции после явного подтверждения. Пустые бланки и сводные поля без отдельных позиций не создают фиктивные активы.

Production Docker image включает Tesseract и языковые пакеты. Для локального запуска установите Tesseract отдельно и добавьте его в PATH либо укажите полный путь в `ASSETGUARD_TESSERACT_CMD`; если модели языков размещены отдельно, задайте их каталог через `ASSETGUARD_TESSDATA_DIR`. На Windows также задайте ASCII-путь к доступной на запись временной папке в `ASSETGUARD_OCR_TEMP_DIR`; это избегает ошибок системной кодировки в путях с кириллицей. Если OCR недоступен или в скане не найдены надёжные отдельные позиции, импорт вернёт понятную ошибку, а не создаст фиктивные активы. Лимиты PDF: 10 MiB; OCR-скан — не более 30 страниц.

## Agent credentials и re-enrolment

`POST /admin/agent-credentials` выдаёт секрет один раз, хранит только PBKDF2 hash и после первой инвентаризации связывает credential с endpoint. Отзыв немедленно запрещает новые отправки.

После переустановки Windows installer создаёт 30-минутный запрос через `/agent/re-enrolments`, используя SMBIOS UUID только для сопоставления. Администратор организации подтверждает запрос в панели; старый активный credential отзывается, новый создаётся без хранения claim token в plaintext, а endpoint и история инвентаризации сохраняются. Решение и ограничения зафиксированы в [ADR-005](../docs/decisions/ADR-005-agent-reenrolment.md).

## Ограничения текущего этапа

- Native endpoint подтверждён GLPI Agent 1.19 и 1.20 на двух реальных Windows-PC через production TLS endpoint; полный fleet lifecycle test на 3–5 ПК ещё не завершён.
- Vision не поддерживает RTSP, quality gate, multi-frame aggregation и автоматический `ANOMALY`.
- Иерархия корпус/этаж/кабинет и привязка Vision к кабинету реализованы; импорт не извлекает из PDF кабинет без явных данных.
- Production HTTPS, R2 backup и isolated restore повторно подтверждены 2026-10-06 на schema `0026` (220 assets, 11 endpoints); [протокол](../docs/quality/project-audit-2026-10-06.md). Vision image volume в backup пока не входит.
- Agent 0.1.8 отделяет hardware collector от SYSTEM delivery task/FIFO; один реальный PC и controlled offline/lost-ACK lab приняты, финальная readiness установка и fleet остаются открыты. [Контракт](../docs/features/agent-continuous-inventory.md).
- Windows installer `0.1.8` остаётся неподписанным и не должен распространяться массово до code signing и проверки update/rollback.

Эти границы предотвращают ситуацию, когда inventory принимается без неизменяемого RawInventory, payload limit и audit trail.
