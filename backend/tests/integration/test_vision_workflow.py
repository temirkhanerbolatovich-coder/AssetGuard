from __future__ import annotations

import asyncio
import io
import os
from datetime import UTC, datetime
from uuid import uuid4

import httpx
from PIL import Image

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.interfaces.http import vision as vision_api
from assetguard.modules.assets.models import BuildingRecord, FloorRecord, OrganizationRecord, RoomRecord
from assetguard.modules.vision.detector import Detection


class SequenceDetector:
    model_id = "fixture-detector"

    def __init__(self) -> None:
        self.calls = 0

    def detect(self, image: Image.Image) -> list[Detection]:
        self.calls += 1
        common = [
            Detection("monitor", 0.95, 10, 10, 80, 70),
            Detection("computer", 0.91, 90, 20, 150, 100),
        ]
        if self.calls == 1:
            common.append(Detection("monitor", 0.89, 160, 10, 225, 70))
        return common


def jpeg_bytes() -> bytes:
    output = io.BytesIO()
    Image.new("RGB", (240, 140), "#dbeafe").save(output, "JPEG")
    return output.getvalue()


def admin_headers() -> dict[str, str]:
    return {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}


def test_vision_upload_baseline_comparison_warning(tmp_path, monkeypatch) -> None:
    original_storage = os.environ.get("ASSETGUARD_VISION_STORAGE_ROOT")
    os.environ["ASSETGUARD_VISION_STORAGE_ROOT"] = str(tmp_path)
    get_settings.cache_clear()
    detector = SequenceDetector()
    monkeypatch.setattr(vision_api, "get_detector", lambda: detector)
    now = datetime.now(UTC)
    with get_session_factory()() as session:
        organization = OrganizationRecord(
            name=f"Vision test school {uuid4().hex[:8]}",
            created_at=datetime(2000, 1, 1, tzinfo=UTC),
        )
        session.add(organization)
        session.flush()
        building = BuildingRecord(organization_id=organization.id, name=f"Vision test building {uuid4().hex[:8]}", created_at=now)
        session.add(building)
        session.flush()
        floor = FloorRecord(building_id=building.id, name="1", created_at=now)
        session.add(floor)
        session.flush()
        room = RoomRecord(floor_id=floor.id, name="305", created_at=now)
        session.add(room)
        session.commit()
        room_id = room.id
    try:
        asyncio.run(_exercise_vision_workflow(room_id))
    finally:
        if original_storage is None:
            os.environ.pop("ASSETGUARD_VISION_STORAGE_ROOT", None)
        else:
            os.environ["ASSETGUARD_VISION_STORAGE_ROOT"] = original_storage
        get_settings.cache_clear()


async def _exercise_vision_workflow(room_id) -> None:
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        asset = await client.post("/admin/assets", headers=admin_headers(), json={
            "inventory_number": "VISION-001", "name": "Vision linked workstation", "asset_type": "Desktop",
            "room_id": str(room_id),
        })
        assert asset.status_code == 201
        first = await client.post(
            "/admin/vision/scans", headers=admin_headers(),
            data={"location_room_id": str(room_id), "asset_id": asset.json()["id"]},
            files={"image": ("room-305-first.jpg", jpeg_bytes(), "image/jpeg")},
        )
        assert first.status_code == 201, first.text
        first_scan = first.json()
        assert first_scan["status"] == "NOT_CHECKED"
        assert first_scan["counts"] == {"computer": 1, "monitor": 2}
        assert first_scan["asset"]["id"] == asset.json()["id"]
        assert len(first_scan["detections"]) == 3

        baseline = await client.post(
            f"/admin/vision/rooms/{first_scan['room_id']}/baseline",
            headers=admin_headers(), json={"scan_id": first_scan["id"]},
        )
        assert baseline.status_code == 200
        assert baseline.json()["counts"] == {"computer": 1, "monitor": 2}

        second = await client.post(
            "/admin/vision/scans", headers=admin_headers(),
            data={"location_room_id": str(room_id)},
            files={"image": ("room-305-second.jpg", jpeg_bytes(), "image/jpeg")},
        )
        assert second.status_code == 201, second.text
        second_scan = second.json()
        assert second_scan["status"] == "WARNING"
        assert second_scan["counts"] == {"computer": 1, "monitor": 1}
        assert second_scan["comparison"]["differences"] == [{
            "class_name": "monitor", "expected": 2, "detected": 1, "difference": -1,
        }]

        image = await client.get(
            f"/admin/vision/scans/{second_scan['id']}/image?kind=annotated",
            headers=admin_headers(),
        )
        assert image.status_code == 200
        assert image.headers["content-type"].startswith("image/jpeg")
        history = await client.get(
            f"/admin/vision/rooms/{first_scan['room_id']}/scans", headers=admin_headers(),
        )
        assert history.status_code == 200
        assert [item["status"] for item in history.json()] == ["WARNING", "OK"]
