from types import SimpleNamespace

import pytest
from fastapi import HTTPException

from assetguard.interfaces.http import qr_support


def test_qr_base_url_uses_configured_url_without_duplicate_slash(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(qr_support, "get_settings", lambda: SimpleNamespace(public_url="https://assetguard.example/app/"))

    assert qr_support.qr_base_url(None) == "https://assetguard.example/app"


def test_qr_base_url_accepts_https_path_and_rejects_unsafe_overrides() -> None:
    assert qr_support.qr_base_url("https://assetguard.example/school/") == "https://assetguard.example/school"

    for value in (
        "http://assetguard.example",
        "https://user:secret@assetguard.example",
        "https://assetguard.example?token=secret",
        "https://assetguard.example/#asset=123",
    ):
        with pytest.raises(HTTPException) as error:
            qr_support.qr_base_url(value)
        assert error.value.status_code == 422
