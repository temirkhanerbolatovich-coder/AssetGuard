from datetime import UTC, datetime, timedelta

import pytest

from assetguard.infrastructure.config import get_settings
from assetguard.modules.endpoints.service import endpoint_connection_status
from assetguard.modules.snapshots.models import ManagedEndpointRecord


@pytest.mark.parametrize("status,age_hours,expected", [
    ("ONLINE", 6, "ONLINE"),
    ("ONLINE", 7, "ONLINE"),
    ("ONLINE", 7.01, "STALE"),
    ("REQUIRES_VERIFICATION", 6, "REQUIRES_VERIFICATION"),
    ("REQUIRES_VERIFICATION", 8, "STALE"),
    ("OFFLINE", 8, "OFFLINE"),
    ("IDENTITY_CONFLICT", 8, "IDENTITY_CONFLICT"),
])
def test_freshness_respects_configuration_and_preserves_stored_state(monkeypatch, status, age_hours, expected):
    monkeypatch.setenv("ASSETGUARD_ENDPOINT_STALE_AFTER_HOURS", "7")
    get_settings.cache_clear()
    now = datetime(2026, 10, 6, 12, tzinfo=UTC)
    last_seen = now - timedelta(hours=age_hours)
    endpoint = ManagedEndpointRecord(status=status, last_seen_at=last_seen, updated_at=last_seen)
    try:
        assert endpoint_connection_status(endpoint, now=now) == expected
        assert (endpoint.status, endpoint.last_seen_at, endpoint.updated_at) == (status, last_seen, last_seen)
    finally:
        get_settings.cache_clear()
