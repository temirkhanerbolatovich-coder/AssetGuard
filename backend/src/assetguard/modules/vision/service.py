from __future__ import annotations

import io
import logging
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from uuid import UUID, uuid4

from PIL import Image, ImageDraw, ImageFont, UnidentifiedImageError
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.modules.vision.detector import Detection, Detector
from assetguard.modules.vision.models import (
    VisionBaselineRecord, VisionDetectionRecord, VisionRoomRecord, VisionScanRecord,
)
from assetguard.modules.assets.models import BuildingRecord, FloorRecord, RoomRecord

logger = logging.getLogger("assetguard.vision")
COLORS = ("#4f8cff", "#35c987", "#f6b84a", "#ff6b7a", "#b48cff", "#41c7d9")


def read_image(payload: bytes) -> Image.Image:
    try:
        image = Image.open(io.BytesIO(payload))
        image.load()
    except (UnidentifiedImageError, OSError) as error:
        raise ValueError("Upload must be a valid JPEG or PNG image.") from error
    if image.width < 32 or image.height < 32 or image.width * image.height > 24_000_000:
        raise ValueError("Image dimensions are outside the supported demo range.")
    return image.convert("RGB")


def create_scan(
    session: Session, *, payload: bytes, detector: Detector, asset_id: UUID | None = None,
    organization_id: UUID | None = None, room_name: str | None = None, room_id: UUID | None = None,
) -> VisionScanRecord:
    settings = get_settings()
    image = read_image(payload)
    if room_id is not None:
        location_room = session.get(RoomRecord, room_id)
        floor = session.get(FloorRecord, location_room.floor_id) if location_room else None
        building = session.get(BuildingRecord, floor.building_id) if floor else None
        if not location_room or not floor or not building or (organization_id and building.organization_id != organization_id):
            raise ValueError("Выбранный кабинет не найден в вашей организации.")
        organization_id = building.organization_id
        normalized_room = f"{building.name} / {floor.name} / {location_room.name}"
        room = session.scalar(select(VisionRoomRecord).where(VisionRoomRecord.location_room_id == location_room.id))
        if room is None:
            room = VisionRoomRecord(
                name=normalized_room, organization_id=organization_id,
                location_room_id=location_room.id, created_at=datetime.now(UTC),
            )
            session.add(room)
            session.flush()
    else:
        normalized_room = " ".join((room_name or "").strip().split())
        if not normalized_room:
            raise ValueError("Выберите кабинет из структуры школы.")
        room = session.scalar(select(VisionRoomRecord).where(VisionRoomRecord.name == normalized_room, VisionRoomRecord.organization_id == organization_id))
        if room is None:
            # Legacy scans can still be opened by administrators, but remain deliberately
            # unlinked and therefore invisible to location-scoped staff.
            room = VisionRoomRecord(name=normalized_room, organization_id=organization_id, created_at=datetime.now(UTC))
            session.add(room)
            session.flush()
    scan_id = uuid4()
    storage = settings.vision_storage_root.resolve()
    storage.mkdir(parents=True, exist_ok=True)
    original_path = storage / f"{scan_id}-original.jpg"
    annotated_path = storage / f"{scan_id}-annotated.jpg"
    logger.info("vision_scan_started scan=%s room=%s bytes=%s", scan_id, room.id, len(payload))
    detections = [item for item in detector.detect(image) if item.confidence >= settings.vision_confidence_threshold]
    counts = dict(sorted(Counter(item.class_name for item in detections).items()))
    baseline = session.scalar(select(VisionBaselineRecord).where(VisionBaselineRecord.room_id == room.id))
    comparison = compare_counts(baseline.counts if baseline else None, counts)
    status = "NOT_CHECKED" if baseline is None else "WARNING" if comparison["differences"] else "OK"
    annotated = annotate(image, detections)
    image.save(original_path, format="JPEG", quality=92, optimize=True)
    annotated.save(annotated_path, format="JPEG", quality=92, optimize=True)
    scan = VisionScanRecord(
        id=scan_id, room_id=room.id, asset_id=asset_id, created_at=datetime.now(UTC), status=status,
        original_image_path=str(original_path), annotated_image_path=str(annotated_path),
        counts=counts, comparison=comparison, model_id=detector.model_id,
        confidence_threshold=settings.vision_confidence_threshold,
    )
    session.add(scan)
    session.flush()
    for item in detections:
        session.add(VisionDetectionRecord(
            scan_id=scan.id, class_name=item.class_name, confidence=item.confidence,
            bbox={"x1": item.x1, "y1": item.y1, "x2": item.x2, "y2": item.y2},
        ))
    session.commit()
    session.refresh(scan)
    logger.info("vision_scan_completed scan=%s detections=%s status=%s", scan.id, len(detections), status)
    return scan


def compare_counts(expected: dict[str, int] | None, detected: dict[str, int]) -> dict:
    if expected is None:
        return {"expected": None, "detected": detected, "differences": []}
    differences = []
    for class_name in sorted(set(expected) | set(detected)):
        expected_count = int(expected.get(class_name, 0))
        detected_count = int(detected.get(class_name, 0))
        if expected_count != detected_count:
            differences.append({
                "class_name": class_name, "expected": expected_count,
                "detected": detected_count, "difference": detected_count - expected_count,
            })
    return {"expected": expected, "detected": detected, "differences": differences}


def accept_baseline(session: Session, room: VisionRoomRecord, scan: VisionScanRecord) -> VisionBaselineRecord:
    if scan.room_id != room.id:
        raise ValueError("The selected scan belongs to another room.")
    now = datetime.now(UTC)
    baseline = session.scalar(select(VisionBaselineRecord).where(VisionBaselineRecord.room_id == room.id))
    if baseline is None:
        baseline = VisionBaselineRecord(
            room_id=room.id, source_scan_id=scan.id, counts=scan.counts,
            created_at=now, updated_at=now,
        )
        session.add(baseline)
    else:
        baseline.source_scan_id = scan.id
        baseline.counts = scan.counts
        baseline.updated_at = now
    scan.status = "OK"
    scan.comparison = compare_counts(scan.counts, scan.counts)
    session.commit()
    session.refresh(baseline)
    logger.info("vision_baseline_accepted room=%s scan=%s", room.id, scan.id)
    return baseline


def annotate(image: Image.Image, detections: list[Detection]) -> Image.Image:
    result = image.copy()
    draw = ImageDraw.Draw(result)
    font = ImageFont.load_default(size=max(12, min(image.size) // 55))
    for index, item in enumerate(detections):
        color = COLORS[index % len(COLORS)]
        width = max(2, min(image.size) // 300)
        draw.rectangle((item.x1, item.y1, item.x2, item.y2), outline=color, width=width)
        label = f"{item.class_name} {item.confidence:.2f}"
        left, top, right, bottom = draw.textbbox((item.x1, item.y1), label, font=font)
        top = max(0, item.y1 - (bottom - top) - 6)
        draw.rectangle((item.x1, top, item.x1 + (right - left) + 8, top + (bottom - top) + 6), fill=color)
        draw.text((item.x1 + 4, top + 3), label, fill="#06101f", font=font)
    return result


def image_path(scan: VisionScanRecord, kind: str) -> Path:
    candidate = Path(scan.annotated_image_path if kind == "annotated" else scan.original_image_path).resolve()
    root = get_settings().vision_storage_root.resolve()
    if root not in candidate.parents or not candidate.is_file():
        raise FileNotFoundError("Vision image is unavailable.")
    return candidate
