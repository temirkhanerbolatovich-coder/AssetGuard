import pytest

from assetguard.modules.inventory.schema import validate_inventory_envelope


def test_glpi_envelope_requires_device_id() -> None:
    with pytest.raises(ValueError, match="deviceid"):
        validate_inventory_envelope({"content": {}}, "GLPI_AGENT")


def test_envelope_allows_source_specific_extra_fields() -> None:
    result = validate_inventory_envelope(
        {"deviceid": "fixture-device", "content": {}, "source_extension": {"version": 1}},
        "GLPI_AGENT",
    )
    assert result.deviceid == "fixture-device"

