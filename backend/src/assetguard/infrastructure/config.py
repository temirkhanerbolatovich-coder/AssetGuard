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
    max_inventory_payload_bytes: int


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
        max_inventory_payload_bytes=int(
            os.environ.get("ASSETGUARD_MAX_INVENTORY_PAYLOAD_BYTES", "2097152")
        ),
    )
