"""Server cadence is explicit, validated and expressed in native GLPI hours."""
from xml.etree import ElementTree

import pytest

from assetguard.infrastructure.config import get_settings
from assetguard.interfaces.http.glpi_agent import inventory_reply


@pytest.mark.parametrize("seconds", ["0", "59", "86401", "invalid"])
def test_glpi_cadence_rejects_invalid_configuration(monkeypatch, seconds):
    monkeypatch.setenv("ASSETGUARD_GLPI_PROLOG_INTERVAL_SECONDS", seconds)
    get_settings.cache_clear()
    try:
        with pytest.raises((ValueError, RuntimeError)):
            get_settings()
    finally:
        get_settings.cache_clear()


def test_glpi_cadence_uses_configured_seconds(monkeypatch):
    monkeypatch.setenv("ASSETGUARD_GLPI_PROLOG_INTERVAL_SECONDS", "600")
    get_settings.cache_clear()
    try:
        reply = ElementTree.fromstring(inventory_reply().body)
        assert float(reply.findtext("PROLOG_FREQ")) * 3600 == pytest.approx(600, abs=0.001)
        assert reply.findtext("RESPONSE") == "SEND"
    finally:
        get_settings.cache_clear()
