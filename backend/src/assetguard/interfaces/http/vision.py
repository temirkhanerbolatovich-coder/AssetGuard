from __future__ import annotations

import logging
from typing import Annotated, Literal
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.interfaces.http.admin_assets import require_admin, require_viewer
from assetguard.modules.vision.detector import get_detector
from assetguard.modules.vision.models import (
    VisionBaselineRecord, VisionDetectionRecord, VisionRoomRecord, VisionScanRecord,
)
from assetguard.modules.vision.service import accept_baseline, create_scan, image_path
from assetguard.modules.assets.models import AssetRecord

logger = logging.getLogger("assetguard.vision")
router = APIRouter(prefix="/admin/vision", tags=["vision"])


class BaselineBody(BaseModel):
    scan_id: UUID


def scan_view(session: Session, scan: VisionScanRecord) -> dict:
    detections = list(session.scalars(select(VisionDetectionRecord).where(
        VisionDetectionRecord.scan_id == scan.id,
    ).order_by(VisionDetectionRecord.class_name, VisionDetectionRecord.confidence.desc())))
    asset = session.get(AssetRecord, scan.asset_id) if scan.asset_id else None
    return {
        "id": str(scan.id), "room_id": str(scan.room_id), "created_at": scan.created_at,
        "asset": None if asset is None else {
            "id": str(asset.id), "inventory_number": asset.inventory_number, "name": asset.name,
        },
        "status": scan.status, "counts": scan.counts, "comparison": scan.comparison,
        "model_id": scan.model_id, "confidence_threshold": scan.confidence_threshold,
        "annotated_image_url": f"/admin/vision/scans/{scan.id}/image?kind=annotated",
        "original_image_url": f"/admin/vision/scans/{scan.id}/image?kind=original",
        "detections": [{
            "id": str(item.id), "class_name": item.class_name,
            "confidence": item.confidence, "bbox": item.bbox,
        } for item in detections],
    }


@router.post("/scans", dependencies=[Depends(require_admin)], status_code=201)
def upload_scan(
    room_name: Annotated[str, Form(min_length=1, max_length=255)],
    image: Annotated[UploadFile, File()],
    session: Annotated[Session, Depends(get_session)],
    asset_id: Annotated[UUID | None, Form()] = None,
):
    settings = get_settings()
    if image.content_type not in {"image/jpeg", "image/png"}:
        raise HTTPException(415, "Only JPEG and PNG images are supported.")
    payload = image.file.read(settings.vision_max_image_bytes + 1)
    if len(payload) > settings.vision_max_image_bytes:
        raise HTTPException(413, "Vision image is too large.")
    try:
        if asset_id and not session.get(AssetRecord, asset_id):
            raise HTTPException(404, "Asset was not found.")
        scan = create_scan(session, room_name=room_name, payload=payload, detector=get_detector(), asset_id=asset_id)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    except RuntimeError as error:
        logger.exception("vision_scan_runtime_error room=%s", room_name)
        raise HTTPException(503, str(error)) from error
    return scan_view(session, scan)


@router.get("/rooms", dependencies=[Depends(require_viewer)])
def rooms(session: Annotated[Session, Depends(get_session)]):
    result = []
    for room in session.scalars(select(VisionRoomRecord).order_by(VisionRoomRecord.name)):
        latest = session.scalar(select(VisionScanRecord).where(
            VisionScanRecord.room_id == room.id,
        ).order_by(VisionScanRecord.created_at.desc()))
        baseline = session.scalar(select(VisionBaselineRecord).where(VisionBaselineRecord.room_id == room.id))
        result.append({
            "id": str(room.id), "name": room.name,
            "latest_scan": scan_view(session, latest) if latest else None,
            "baseline": None if not baseline else {
                "id": str(baseline.id), "source_scan_id": str(baseline.source_scan_id),
                "counts": baseline.counts, "updated_at": baseline.updated_at,
            },
        })
    return result


@router.get("/rooms/{room_id}/scans", dependencies=[Depends(require_viewer)])
def room_scans(room_id: UUID, session: Annotated[Session, Depends(get_session)]):
    if not session.get(VisionRoomRecord, room_id):
        raise HTTPException(404, "Vision room was not found.")
    return [scan_view(session, scan) for scan in session.scalars(select(VisionScanRecord).where(
        VisionScanRecord.room_id == room_id,
    ).order_by(VisionScanRecord.created_at.desc()))]


@router.get("/scans/{scan_id}", dependencies=[Depends(require_viewer)])
def scan_detail(scan_id: UUID, session: Annotated[Session, Depends(get_session)]):
    scan = session.get(VisionScanRecord, scan_id)
    if not scan:
        raise HTTPException(404, "Vision scan was not found.")
    return scan_view(session, scan)


@router.get("/scans/{scan_id}/image", dependencies=[Depends(require_viewer)])
def scan_image(
    scan_id: UUID, session: Annotated[Session, Depends(get_session)],
    kind: Literal["original", "annotated"] = "annotated",
):
    scan = session.get(VisionScanRecord, scan_id)
    if not scan:
        raise HTTPException(404, "Vision scan was not found.")
    try:
        path = image_path(scan, kind)
    except FileNotFoundError as error:
        raise HTTPException(404, str(error)) from error
    return FileResponse(path, media_type="image/jpeg", filename=path.name)


@router.get("/rooms/{room_id}/baseline", dependencies=[Depends(require_viewer)])
def get_baseline(room_id: UUID, session: Annotated[Session, Depends(get_session)]):
    baseline = session.scalar(select(VisionBaselineRecord).where(VisionBaselineRecord.room_id == room_id))
    return None if baseline is None else {
        "id": str(baseline.id), "room_id": str(baseline.room_id),
        "source_scan_id": str(baseline.source_scan_id), "counts": baseline.counts,
        "created_at": baseline.created_at, "updated_at": baseline.updated_at,
    }


@router.post("/rooms/{room_id}/baseline", dependencies=[Depends(require_admin)])
def save_baseline(room_id: UUID, body: BaselineBody, session: Annotated[Session, Depends(get_session)]):
    room = session.get(VisionRoomRecord, room_id)
    scan = session.get(VisionScanRecord, body.scan_id)
    if not room or not scan:
        raise HTTPException(404, "Vision room or scan was not found.")
    try:
        baseline = accept_baseline(session, room, scan)
    except ValueError as error:
        raise HTTPException(422, str(error)) from error
    return {
        "id": str(baseline.id), "room_id": str(baseline.room_id),
        "source_scan_id": str(baseline.source_scan_id), "counts": baseline.counts,
        "updated_at": baseline.updated_at,
    }
