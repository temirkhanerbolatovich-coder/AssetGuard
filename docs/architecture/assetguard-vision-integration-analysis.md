# AssetGuard Vision — минимальная интеграция

> **Исторический документ.** Даты, SHA, измерения и исходные требования ниже относятся к описанному этапу. Сверка указателя выполнена 2026-10-06; текущее состояние и оставшаяся работа — в [checklist](../product/current-project-checklist.md) и [аудите](../quality/project-audit-2026-10-06.md).

## Решение

Для демонстрационного MVP Vision добавлен как изолированный модуль существующего FastAPI modular monolith. Это минимальный путь: используются текущие PostgreSQL, SQLAlchemy/Alembic, `/admin/*` authentication, единый Dashboard и принятая структура `modules`/`interfaces`. Отдельный microservice не требовался и увеличил бы число точек отказа.

`Dashboard multipart upload → /admin/vision/scans → lazy Grounding DINO inference → original/annotated JPEG → PostgreSQL scan/detections/counts → explicit room baseline → comparison → WARNING`

## Что добавлено

- `modules/vision`: адаптер Grounding DINO, image validation/annotation и baseline comparison;
- router `/admin/vision/*`, использующий существующие ADMIN/VIEWER guards;
- таблицы `vision_rooms`, `vision_scans`, `vision_detections`, `vision_baselines`;
- локальное image storage `.local/vision` для demo;
- блок Dashboard с upload, annotated image, counts, baseline и history;
- integration test всего workflow с детерминированным detector;
- реальный smoke test на Grounding DINO и demo-паре изображений.

Модель загружается лениво при первом scan. Поэтому отсутствие ML dependencies или сбой inference возвращает ошибку только Vision endpoint и не мешает старту основного AssetGuard API.

## Осознанно не реализовано

- отдельный inference service/container и S3-compatible storage;
- RTSP/cameras/scheduler, video, tracking и распознавание людей;
- `ANOMALY`, автоматическое подтверждение пропажи и уведомления;
- сопоставление физической detection с конкретным endpoint/asset;
- обучение/калибровка модели и production accuracy guarantees.

Эти функции не нужны для требуемого demo-сценария. Текущий `WARNING` означает только расхождение counts с baseline, а не доказанную пропажу.

## Ограничения demo

Grounding DINO tiny — zero-shot detector: классы и threshold конфигурируются, но counts чувствительны к ракурсу, освещению и перекрытиям. Снимки сохраняются локально, а inference на CPU может быть медленным. Для production следующим отдельным этапом понадобятся dataset/accuracy evaluation, устойчивое object storage, retention/access policy и решение о GPU или отдельном Vision Service.
