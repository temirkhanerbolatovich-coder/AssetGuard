"""Raw inventory evidence model boundary.

The ORM mapping is intentionally deferred until the ingest application service is
implemented. This module reserves the domain boundary for immutable payloads.
"""

import hashlib
import json
from dataclasses import dataclass
from datetime import datetime
from typing import Any
from uuid import UUID


@dataclass(frozen=True, slots=True)
class RawInventoryEvidence:
    """Immutable evidence received from an inventory source."""

    id: UUID
    source: str
    received_at: datetime
    payload_hash: str
    payload: dict[str, Any]


def payload_sha256(payload: dict[str, Any]) -> str:
    """Create a stable semantic hash while retaining the original JSONB payload."""
    canonical_payload = json.dumps(
        payload,
        ensure_ascii=False,
        separators=(",", ":"),
        sort_keys=True,
    ).encode("utf-8")
    return hashlib.sha256(canonical_payload).hexdigest()
