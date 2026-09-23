"""Runtime configuration loaded from environment, never source control."""

from __future__ import annotations

import os
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv


# This resolves to the repository root even when the source is reached through
# the local ASCII junction used by the current Windows development environment.
load_dotenv(Path(__file__).resolve().parents[4] / ".env", override=False)


@dataclass(frozen=True, slots=True)
class Settings:
    database_url: str
    inventory_shared_secret: str
    admin_shared_secret: str
    viewer_shared_secret: str | None
    previous_inventory_shared_secret: str | None
    previous_admin_shared_secret: str | None
    max_inventory_payload_bytes: int
    rate_limit_per_minute: int
    endpoint_stale_after_hours: int
    vision_model_id: str
    vision_confidence_threshold: float
    vision_classes: tuple[str, ...]
    vision_storage_root: Path
    vision_max_image_bytes: int


@lru_cache
def get_settings() -> Settings:
    database_url = os.environ.get("ASSETGUARD_DATABASE_URL")
    inventory_shared_secret = os.environ.get("ASSETGUARD_INVENTORY_SHARED_SECRET")
    admin_shared_secret = os.environ.get("ASSETGUARD_ADMIN_SHARED_SECRET")
    if not database_url:
        raise RuntimeError("ASSETGUARD_DATABASE_URL must be configured.")
    if not inventory_shared_secret:
        raise RuntimeError("ASSETGUARD_INVENTORY_SHARED_SECRET must be configured.")
    if not admin_shared_secret:
        raise RuntimeError("ASSETGUARD_ADMIN_SHARED_SECRET must be configured.")

    return Settings(
        database_url=database_url,
        inventory_shared_secret=inventory_shared_secret,
        admin_shared_secret=admin_shared_secret,
        viewer_shared_secret=os.environ.get("ASSETGUARD_VIEWER_SHARED_SECRET"),
        previous_inventory_shared_secret=os.environ.get("ASSETGUARD_PREVIOUS_INVENTORY_SHARED_SECRET"),
        previous_admin_shared_secret=os.environ.get("ASSETGUARD_PREVIOUS_ADMIN_SHARED_SECRET"),
        max_inventory_payload_bytes=int(
            os.environ.get("ASSETGUARD_MAX_INVENTORY_PAYLOAD_BYTES", "2097152")
        ),
        rate_limit_per_minute=int(os.environ.get("ASSETGUARD_RATE_LIMIT_PER_MINUTE", "120")),
        endpoint_stale_after_hours=int(os.environ.get("ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS", "24")),
        vision_model_id=os.environ.get("ASSETGUARD_VISION_MODEL_ID", "IDEA-Research/grounding-dino-tiny"),
        vision_confidence_threshold=float(os.environ.get("ASSETGUARD_VISION_CONFIDENCE_THRESHOLD", "0.35")),
        vision_classes=tuple(item.strip().lower() for item in os.environ.get(
            "ASSETGUARD_VISION_CLASSES",
            "monitor,computer,printer,projector,television,keyboard,laptop,chair,table",
        ).split(",") if item.strip()),
        vision_storage_root=Path(os.environ.get(
            "ASSETGUARD_VISION_STORAGE_ROOT",
            str(Path(__file__).resolve().parents[4] / ".local" / "vision"),
        )),
        vision_max_image_bytes=int(os.environ.get("ASSETGUARD_VISION_MAX_IMAGE_BYTES", "10485760")),
    )
