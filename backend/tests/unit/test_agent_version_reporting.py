from assetguard.interfaces.http.admin_assets import (
    _agent_version_status,
    _installer_version,
)


def test_assetguard_installer_version_is_read_from_inventory_tag() -> None:
    assert _installer_version({"tag": ["school-42", "assetguard-installer-0.1.7"]}) == "0.1.7"


def test_untrusted_or_unrelated_installer_tags_are_not_reported() -> None:
    assert _installer_version({"tag": ["assetguard-installer-", "other-product-9.9.9"]}) is None
    assert _installer_version({"tag": [{"unexpected": "object"}]}) is None


def test_agent_version_support_status_is_explicit() -> None:
    assert _agent_version_status("1.20") == "SUPPORTED"
    assert _agent_version_status("1.21") == "UNSUPPORTED"
    assert _agent_version_status(None) == "UNKNOWN"
