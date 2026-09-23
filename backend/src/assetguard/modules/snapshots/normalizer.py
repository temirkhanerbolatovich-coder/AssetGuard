"""GLPI-shaped inventory normalization for the MVP device card and hardware diff."""
from __future__ import annotations
from datetime import UTC, datetime
from typing import Any
from sqlalchemy import select
from sqlalchemy.orm import Session
from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.snapshots.models import ComponentIdentityRecord, ComponentObservationRecord, EndpointIdentifierRecord, HardwareSnapshotRecord, ManagedEndpointRecord

NORMALIZER_VERSION = "0.1"
INVALID_IDENTIFIERS = {"", "00000000", "UNKNOWN", "DEFAULT STRING", "TO BE FILLED BY O.E.M."}

def normalize_identifier(value: Any) -> str | None:
    if not isinstance(value, str): return None
    normalized = " ".join(value.strip().upper().split())
    if normalized in INVALID_IDENTIFIERS or set(normalized) <= {"0"} or set(normalized) <= {"F"}: return None
    return normalized

def text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None

def integer(value: Any) -> int | None:
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None

def normalize_raw_inventory(session: Session, raw: RawInventoryRecord) -> HardwareSnapshotRecord:
    existing = session.scalar(select(HardwareSnapshotRecord).where(HardwareSnapshotRecord.raw_inventory_id == raw.id))
    if existing: return existing
    content = raw.payload.get("content") if isinstance(raw.payload, dict) else None
    if not isinstance(content, dict):
        raw.processing_status, raw.processing_error = "FAILED", "Inventory content is not a JSON object."; session.commit(); raise ValueError(raw.processing_error)
    now = datetime.now(UTC); hardware = content.get("hardware") if isinstance(content.get("hardware"), dict) else {}
    raw_uuid, normalized_uuid = text(hardware.get("uuid")), normalize_identifier(hardware.get("uuid")); endpoint = None
    if normalized_uuid:
        identifier = session.scalar(select(EndpointIdentifierRecord).where(EndpointIdentifierRecord.identifier_type == "SMBIOS_UUID", EndpointIdentifierRecord.normalized_value == normalized_uuid))
        if identifier: endpoint = session.get(ManagedEndpointRecord, identifier.managed_endpoint_id)
    if endpoint is None:
        endpoint = ManagedEndpointRecord(source=raw.source, source_agent_id=text(raw.payload.get("deviceid")), hostname=text(hardware.get("name")), last_seen_at=raw.received_at, status="ONLINE" if normalized_uuid else "REQUIRES_VERIFICATION", created_at=now, updated_at=now); session.add(endpoint); session.flush()
        if normalized_uuid and raw_uuid: session.add(EndpointIdentifierRecord(managed_endpoint_id=endpoint.id, identifier_type="SMBIOS_UUID", raw_value=raw_uuid, normalized_value=normalized_uuid, confidence="HIGH", first_seen_at=now, last_seen_at=now, is_active=True))
    else:
        endpoint.hostname = text(hardware.get("name")) or endpoint.hostname; endpoint.last_seen_at = raw.received_at; endpoint.updated_at = now
    memories = content.get("memories") if isinstance(content.get("memories"), list) else []
    storages = content.get("storages") if isinstance(content.get("storages"), list) else []
    cpus = content.get("cpus") if isinstance(content.get("cpus"), list) else []
    videos = content.get("videos") if isinstance(content.get("videos"), list) else []
    snapshot = HardwareSnapshotRecord(managed_endpoint_id=endpoint.id, raw_inventory_id=raw.id, captured_at=raw.received_at, created_at=now, snapshot_type="FULL" if raw.inventory_type == "FULL" else "PARTIAL", completeness={"RAM": "COMPLETE" if isinstance(content.get("memories"), list) else "UNOBSERVED", "STORAGE": "COMPLETE" if isinstance(content.get("storages"), list) else "UNOBSERVED", "CPU": "OBSERVED" if isinstance(content.get("cpus"), list) else "UNOBSERVED", "GPU": "OBSERVED" if isinstance(content.get("videos"), list) else "UNOBSERVED"}, normalizer_version=NORMALIZER_VERSION); session.add(snapshot); session.flush()
    _add_observations(session, snapshot, "RAM", [x for x in memories if isinstance(x, dict)])
    _add_observations(session, snapshot, "STORAGE", [x for x in storages if isinstance(x, dict)])
    _add_observations(session, snapshot, "CPU", [x for x in cpus if isinstance(x, dict)])
    _add_observations(session, snapshot, "GPU", [x for x in videos if isinstance(x, dict)])
    raw.managed_endpoint_id, raw.processing_status, raw.processing_error = endpoint.id, "PROCESSED", None; session.commit(); session.refresh(snapshot); return snapshot

def _add_observations(session: Session, snapshot: HardwareSnapshotRecord, component_type: str, items: list[dict[str, Any]]) -> None:
    for item in items:
        raw_serial = text(item.get("serialnumber") if component_type == "RAM" else item.get("serial")); serial = normalize_identifier(raw_serial)
        model = text(item.get("description")) or text(item.get("caption")) or text(item.get("model")) or text(item.get("name")); slot = text(item.get("numslots")) if component_type == "RAM" else None
        capacity = integer(item.get("capacity") if component_type == "RAM" else item.get("disksize") if component_type == "STORAGE" else item.get("memory") if component_type == "GPU" else None); identity = None
        if serial:
            identity = session.scalar(select(ComponentIdentityRecord).where(ComponentIdentityRecord.component_type == component_type, ComponentIdentityRecord.canonical_serial == serial))
            if identity is None:
                identity = ComponentIdentityRecord(component_type=component_type, canonical_serial=serial, manufacturer=text(item.get("manufacturer")), model=model, part_number=text(item.get("partnumber")), identity_confidence="HIGH", created_at=datetime.now(UTC)); session.add(identity); session.flush()
        confidence = "HIGH" if serial else "MEDIUM" if model and (capacity is not None or slot) else "LOW"
        source_key = serial or "|".join(x for x in (model, str(capacity) if capacity is not None else None, slot) if x)
        session.add(ComponentObservationRecord(hardware_snapshot_id=snapshot.id, component_type=component_type, component_identity_id=identity.id if identity else None, manufacturer=text(item.get("manufacturer")), model=model, serial_number=raw_serial, part_number=text(item.get("partnumber")), capacity=capacity, slot=slot, source_key=source_key or None, confidence=confidence, raw_data=item))
