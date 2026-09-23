"""Version-tolerant validation for inventory envelopes at the core boundary."""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, ConfigDict, Field, ValidationError


class InventoryEnvelope(BaseModel):
    """Minimum contract shared by GLPI-shaped fixtures and future adapters."""

    model_config = ConfigDict(extra="allow")

    content: dict[str, Any]
    action: str | None = Field(default=None, max_length=64)
    deviceid: str | None = Field(default=None, max_length=255)
    itemtype: str | None = Field(default=None, max_length=64)


def validate_inventory_envelope(payload: dict[str, Any], source: str) -> InventoryEnvelope:
    try:
        envelope = InventoryEnvelope.model_validate(payload)
    except ValidationError as error:
        raise ValueError(f"Inventory envelope is invalid: {error.errors(include_url=False)}") from error
    if source == "GLPI_AGENT" and not envelope.deviceid:
        raise ValueError("GLPI Agent inventory must include a non-empty deviceid.")
    return envelope
