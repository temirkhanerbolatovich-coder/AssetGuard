"""GLPI-shaped inventory normalization for endpoint identity and hardware diff."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from assetguard.modules.inventory.models import RawInventoryRecord
from assetguard.modules.inventory.schema import validate_inventory_envelope
from assetguard.modules.history.service import append_history
from assetguard.modules.snapshots.models import (
    ComponentIdentityRecord,
    ComponentObservationRecord,
    EndpointIdentifierRecord,
    HardwareSnapshotRecord,
    ManagedEndpointRecord,
)

NORMALIZER_VERSION = "0.2"
INVALID_IDENTIFIERS = {
    "", "00000000", "UNKNOWN", "DEFAULT STRING", "TO BE FILLED BY O.E.M.",
    "NOT SPECIFIED", "NONE", "N/A", "SYSTEM SERIAL NUMBER",
}


def normalize_identifier(value: Any) -> str | None:
    if not isinstance(value, str):
        return None
    normalized = " ".join(value.strip().upper().split())
    compact = normalized.replace("-", "").replace(":", "").replace(" ", "")
    if normalized in INVALID_IDENTIFIERS or not compact:
        return None
    if set(compact) <= {"0"} or set(compact) <= {"F"}:
        return None
    return normalized


def text(value: Any) -> str | None:
    return value.strip() if isinstance(value, str) and value.strip() else None


def integer(value: Any) -> int | None:
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return int(value) if isinstance(value, (int, float)) and not isinstance(value, bool) and value >= 0 else None


def _candidate(kind: str, raw: Any, confidence: str) -> tuple[str, str, str, str] | None:
    raw_text = text(raw)
    normalized = normalize_identifier(raw_text)
    if not raw_text or not normalized:
        return None
    return kind, raw_text, normalized, confidence


def _identifier_candidates(payload: dict[str, Any], content: dict[str, Any]) -> list[tuple[str, str, str, str]]:
    hardware = content.get("hardware") if isinstance(content.get("hardware"), dict) else {}
    bios = content.get("bios") if isinstance(content.get("bios"), dict) else {}
    candidates = [
        _candidate("SMBIOS_UUID", hardware.get("uuid"), "HIGH"),
        _candidate("CHASSIS_SERIAL", bios.get("ssn") or bios.get("serial") or bios.get("serialnumber"), "HIGH"),
        _candidate("MOTHERBOARD_SERIAL", bios.get("msn") or bios.get("mserial"), "HIGH"),
        _candidate("BIOS_SERIAL", bios.get("bserial"), "MEDIUM"),
        _candidate("AGENT_DEVICE_ID", payload.get("deviceid"), "MEDIUM"),
    ]
    for board in content.get("motherboards") or []:
        if isinstance(board, dict):
            candidates.append(_candidate("MOTHERBOARD_SERIAL", board.get("serial") or board.get("serialnumber"), "HIGH"))
    for network in content.get("networks") or []:
        if isinstance(network, dict):
            candidates.append(_candidate("MAC", network.get("macaddr") or network.get("mac"), "MEDIUM"))
    result: list[tuple[str, str, str, str]] = []
    seen: set[tuple[str, str]] = set()
    for item in candidates:
        if item and (item[0], item[2]) not in seen:
            result.append(item)
            seen.add((item[0], item[2]))
    return result


def normalize_raw_inventory(session: Session, raw: RawInventoryRecord) -> HardwareSnapshotRecord:
    existing = session.scalar(select(HardwareSnapshotRecord).where(HardwareSnapshotRecord.raw_inventory_id == raw.id))
    if existing:
        return existing
    try:
        envelope = validate_inventory_envelope(raw.payload, raw.source)
        content = envelope.content
    except ValueError as error:
        raw.processing_status = "FAILED"
        raw.processing_error = str(error)
        session.commit()
        raise

    now = datetime.now(UTC)
    hardware = content.get("hardware") if isinstance(content.get("hardware"), dict) else {}
    candidates = _identifier_candidates(raw.payload, content)
    endpoint: ManagedEndpointRecord | None = None
    matched_endpoint_ids: set = set()
    for kind, _, normalized, _ in candidates:
        identifier = session.scalar(select(EndpointIdentifierRecord).where(
            EndpointIdentifierRecord.identifier_type == kind,
            EndpointIdentifierRecord.normalized_value == normalized,
        ))
        if identifier:
            matched_endpoint_ids.add(identifier.managed_endpoint_id)
    if len(matched_endpoint_ids) > 1:
        for endpoint_id in matched_endpoint_ids:
            conflicted = session.get(ManagedEndpointRecord, endpoint_id)
            if conflicted:
                conflicted.status = "IDENTITY_CONFLICT"
                conflicted.updated_at = now
        raw.processing_status = "FAILED"
        raw.processing_error = "Observed identifiers resolve to multiple managed endpoints."
        session.commit()
        raise ValueError(raw.processing_error)
    if matched_endpoint_ids:
        endpoint = session.get(ManagedEndpointRecord, next(iter(matched_endpoint_ids)))

    observed_hostname = text(hardware.get("name"))
    current_hostname = observed_hostname or text(raw.payload.get("deviceid"))
    previous_hostname: str | None = None
    if endpoint is None:
        endpoint = ManagedEndpointRecord(
            source=raw.source,
            source_agent_id=text(raw.payload.get("deviceid")),
            hostname=current_hostname,
            last_seen_at=raw.received_at,
            status="ONLINE" if candidates else "REQUIRES_VERIFICATION",
            created_at=now,
            updated_at=now,
        )
        session.add(endpoint)
        session.flush()
    else:
        previous_hostname = endpoint.hostname
        endpoint.hostname = observed_hostname or endpoint.hostname
        endpoint.source_agent_id = text(raw.payload.get("deviceid")) or endpoint.source_agent_id
        endpoint.last_seen_at = raw.received_at
        endpoint.status = "ONLINE"
        endpoint.updated_at = now

    identity_changes: list[dict[str, str]] = []
    strong_identity_types = {"SMBIOS_UUID", "BIOS_SERIAL", "CHASSIS_SERIAL", "MOTHERBOARD_SERIAL"}
    for kind, raw_value, normalized, confidence in candidates:
        identifier = session.scalar(select(EndpointIdentifierRecord).where(
            EndpointIdentifierRecord.identifier_type == kind,
            EndpointIdentifierRecord.normalized_value == normalized,
        ))
        if identifier:
            identifier.last_seen_at = now
            identifier.is_active = True
        else:
            previous_identifiers = list(session.scalars(select(EndpointIdentifierRecord).where(
                EndpointIdentifierRecord.managed_endpoint_id == endpoint.id,
                EndpointIdentifierRecord.identifier_type == kind,
                EndpointIdentifierRecord.is_active.is_(True),
            )))
            if kind in strong_identity_types:
                for previous in previous_identifiers:
                    previous.is_active = False
                    identity_changes.append({
                        "identifier_type": kind,
                        "previous": previous.normalized_value,
                        "current": normalized,
                    })
            session.add(EndpointIdentifierRecord(
                managed_endpoint_id=endpoint.id,
                identifier_type=kind,
                raw_value=raw_value,
                normalized_value=normalized,
                confidence=confidence,
                first_seen_at=now,
                last_seen_at=now,
                is_active=True,
            ))

    memories = content.get("memories") if isinstance(content.get("memories"), list) else []
    storages = content.get("storages") if isinstance(content.get("storages"), list) else []
    cpus = content.get("cpus") if isinstance(content.get("cpus"), list) else []
    videos = content.get("videos") if isinstance(content.get("videos"), list) else []
    motherboards = content.get("motherboards") if isinstance(content.get("motherboards"), list) else []
    networks = content.get("networks") if isinstance(content.get("networks"), list) else []
    monitors = content.get("monitors") if isinstance(content.get("monitors"), list) else []
    full = raw.inventory_type == "FULL"
    snapshot = HardwareSnapshotRecord(
        managed_endpoint_id=endpoint.id,
        raw_inventory_id=raw.id,
        captured_at=raw.received_at,
        created_at=now,
        snapshot_type="FULL" if full else "PARTIAL",
        completeness={
            "RAM": "COMPLETE" if full and isinstance(content.get("memories"), list) else "UNOBSERVED",
            "STORAGE": "COMPLETE" if full and isinstance(content.get("storages"), list) else "UNOBSERVED",
            "CPU": "OBSERVED" if isinstance(content.get("cpus"), list) else "UNOBSERVED",
            "GPU": "OBSERVED" if isinstance(content.get("videos"), list) else "UNOBSERVED",
            "MOTHERBOARD": "OBSERVED" if isinstance(content.get("motherboards"), list) else "UNOBSERVED",
            "NETWORK": "OBSERVED" if isinstance(content.get("networks"), list) else "UNOBSERVED",
            "MONITOR": "OBSERVED" if isinstance(content.get("monitors"), list) else "UNOBSERVED",
        },
        normalizer_version=NORMALIZER_VERSION,
    )
    session.add(snapshot)
    session.flush()
    _add_observations(session, snapshot, "RAM", [x for x in memories if isinstance(x, dict)])
    _add_observations(session, snapshot, "STORAGE", [x for x in storages if isinstance(x, dict)])
    _add_observations(session, snapshot, "CPU", [x for x in cpus if isinstance(x, dict)])
    _add_observations(session, snapshot, "GPU", [x for x in videos if isinstance(x, dict)])
    _add_observations(session, snapshot, "MOTHERBOARD", [x for x in motherboards if isinstance(x, dict)])
    _add_observations(session, snapshot, "NETWORK", [x for x in networks if isinstance(x, dict)])
    _add_observations(session, snapshot, "MONITOR", [x for x in monitors if isinstance(x, dict)])
    raw.managed_endpoint_id = endpoint.id
    raw.processing_status = "PROCESSED"
    raw.processing_error = None
    append_history(
        session, endpoint=endpoint, event_type="INVENTORY_COMPLETED",
        related_entity_type="RawInventory", related_entity_id=raw.id,
        message="Inventory completed successfully.",
        metadata={"snapshot_id": str(snapshot.id), "inventory_type": snapshot.snapshot_type},
        occurred_at=raw.received_at,
    )
    session.commit()
    session.refresh(snapshot)
    if previous_hostname and observed_hostname and previous_hostname.casefold() != observed_hostname.casefold():
        snapshot._hostname_change = (previous_hostname, observed_hostname)  # type: ignore[attr-defined]
    if identity_changes:
        snapshot._identity_changes = identity_changes  # type: ignore[attr-defined]
    return snapshot


def _add_observations(
    session: Session, snapshot: HardwareSnapshotRecord, component_type: str, items: list[dict[str, Any]],
) -> None:
    for item in items:
        serial_fields = {
            "RAM": ("serialnumber", "serial"),
            "MOTHERBOARD": ("serial", "serialnumber"),
            "NETWORK": ("macaddr", "mac"),
            "MONITOR": ("serial", "serialnumber"),
        }
        fields = serial_fields.get(component_type, ("serial", "serialnumber"))
        raw_serial = next((text(item.get(field)) for field in fields if text(item.get(field))), None)
        serial = normalize_identifier(raw_serial)
        model = text(item.get("description")) or text(item.get("caption")) or text(item.get("model")) or text(item.get("name"))
        slot = text(item.get("numslots")) if component_type == "RAM" else text(item.get("slot"))
        capacity = integer(
            item.get("capacity") if component_type == "RAM"
            else item.get("disksize") if component_type == "STORAGE"
            else item.get("memory") if component_type == "GPU" else None
        )
        identity = None
        if serial:
            identity = session.scalar(select(ComponentIdentityRecord).where(
                ComponentIdentityRecord.component_type == component_type,
                ComponentIdentityRecord.canonical_serial == serial,
            ))
            if identity is None:
                identity = ComponentIdentityRecord(
                    component_type=component_type, canonical_serial=serial,
                    manufacturer=text(item.get("manufacturer")), model=model,
                    part_number=text(item.get("partnumber")), identity_confidence="HIGH",
                    created_at=datetime.now(UTC),
                )
                session.add(identity)
                session.flush()
        confidence = "HIGH" if serial else "MEDIUM" if model and (capacity is not None or slot) else "LOW"
        source_key = serial or "|".join(x for x in (model, str(capacity) if capacity is not None else None, slot) if x)
        session.add(ComponentObservationRecord(
            hardware_snapshot_id=snapshot.id, component_type=component_type,
            component_identity_id=identity.id if identity else None,
            manufacturer=text(item.get("manufacturer")), model=model,
            serial_number=raw_serial, part_number=text(item.get("partnumber")),
            capacity=capacity, slot=slot, source_key=source_key or None,
            confidence=confidence, raw_data=item,
        ))
