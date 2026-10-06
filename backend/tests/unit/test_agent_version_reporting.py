import pytest

from assetguard.interfaces.http.admin_assets import (
    _agent_version_status,
    _installer_version,
)


def test_assetguard_installer_version_is_read_from_inventory_tag() -> None:
    assert _installer_version({"tag": ["school-42", "assetguard-installer-0.1.7"]}) == "0.1.7"


def test_untrusted_or_unrelated_installer_tags_are_not_reported() -> None:
    assert _installer_version({"tag": ["assetguard-installer-", "other-product-9.9.9"]}) is None
    assert _installer_version({"tag": [{"unexpected": "object"}]}) is None


@pytest.mark.parametrize("version", ["1.19", "1.20", "GLPI-Agent_v1.19", "GLPI-Agent_v1.20", " GLPI-Agent_v1.20 "])
def test_supported_glpi_xml_version_representations(version: str) -> None:
    assert _agent_version_status(version) == "SUPPORTED"


@pytest.mark.parametrize("version", ["1.21", "GLPI-Agent_v1.21", "1.20.0", "1.200", "Other-Agent_v1.20", "GLPI-Agent_v1.20-extra", " "])
def test_unverified_versions_remain_unsupported(version: str) -> None:
    assert _agent_version_status(version) == "UNSUPPORTED"


@pytest.mark.parametrize("version", [None, ""])
def test_missing_agent_version_is_unknown(version: str | None) -> None:
    assert _agent_version_status(version) == "UNKNOWN"
