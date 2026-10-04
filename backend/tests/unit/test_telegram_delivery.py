from datetime import UTC, datetime
from io import BytesIO
import json
from urllib.error import HTTPError, URLError
from uuid import uuid4

import pytest

from assetguard.modules.notifications import delivery


def settings():
    return delivery.TelegramSettings("123:test-only-placeholder", "-123", uuid4(), "https://example.invalid")


def payload():
    return {"title": "Расхождение", "subject": "PC-1", "context": "Проверьте данные",
            "severity": "HIGH", "route": "#incident=" + str(uuid4()), "occurred_at": datetime.now(UTC).isoformat()}


@pytest.mark.parametrize("response,code", [
    ({"ok": False}, "NOT_ACCEPTED"),
    ({"ok": True, "result": {}}, "NO_MESSAGE_ID"),
    ({"ok": True, "result": {"message_id": True}}, "NO_MESSAGE_ID"),
    ({"ok": True, "result": {"message_id": 7, "chat": {"id": -456}}}, "WRONG_DESTINATION"),
])
def test_acceptance_requires_message_id_and_expected_destination(monkeypatch, response, code):
    monkeypatch.setattr(delivery, "urlopen", lambda *args, **kwargs: BytesIO(json.dumps(response).encode()))
    with pytest.raises(delivery.TelegramDeliveryError, match=code):
        delivery.send_message(settings(), payload())


def test_success_uses_bounded_plain_text_and_deep_link(monkeypatch):
    requests = []
    def accept(request, timeout):
        requests.append(json.loads(request.data))
        assert timeout == 10
        return BytesIO(b'{"ok":true,"result":{"message_id":7,"chat":{"id":-123}}}')
    monkeypatch.setattr(delivery, "urlopen", accept)
    event = payload()
    event["subject"] = "<b>PC-1</b>"
    assert delivery.send_message(settings(), event) == 7
    assert requests[0]["chat_id"] == "-123"
    assert "parse_mode" not in requests[0]
    assert len(requests[0]["text"]) <= 3500
    assert requests[0]["reply_markup"]["inline_keyboard"][0][0]["url"] == "https://example.invalid/" + event["route"]


def test_rate_limit_preserves_retry_after_without_leaking_token(monkeypatch):
    configured = settings()
    def limited(*args, **kwargs):
        raise HTTPError("https://api.telegram.org/bot" + configured.bot_token, 429, "secret", {}, BytesIO(b'{"parameters":{"retry_after":150}}'))
    monkeypatch.setattr(delivery, "urlopen", limited)
    with pytest.raises(delivery.TelegramDeliveryError) as error:
        delivery.send_message(configured, payload())
    assert error.value.retry_after == 150
    assert str(error.value) == "HTTP_429"
    assert configured.bot_token not in str(error.value)


def test_network_failure_remains_retriable_and_does_not_expose_url(monkeypatch):
    def offline(*args, **kwargs):
        raise URLError("private transport details")
    monkeypatch.setattr(delivery, "urlopen", offline)
    with pytest.raises(delivery.TelegramDeliveryError, match="NETWORK_ERROR"):
        delivery.send_message(settings(), payload())


@pytest.mark.parametrize("event", [None, [], {"route": []}, {"route": "#overview", "occurred_at": None}])
def test_malformed_payload_is_a_bounded_delivery_failure(event):
    with pytest.raises(delivery.TelegramDeliveryError, match="INVALID_(PAYLOAD|ROUTE)"):
        delivery.message_body(event, "https://example.invalid")


def test_configuration_requires_organization_and_safe_https_url(monkeypatch):
    monkeypatch.setenv("ASSETGUARD_TELEGRAM_BOT_TOKEN", "123:test-only-placeholder")
    monkeypatch.setenv("ASSETGUARD_TELEGRAM_CHAT_ID", "-123")
    monkeypatch.setenv("ASSETGUARD_TELEGRAM_ORGANIZATION_ID", str(uuid4()))
    for url in ["http://example.invalid", "https://name:password@example.invalid", "https://example.invalid?token=private"]:
        monkeypatch.setenv("ASSETGUARD_PUBLIC_URL", url)
        with pytest.raises(ValueError): delivery.TelegramSettings.from_environment()
    monkeypatch.setenv("ASSETGUARD_PUBLIC_URL", "https://example.invalid")
    monkeypatch.delenv("ASSETGUARD_TELEGRAM_ORGANIZATION_ID")
    with pytest.raises(ValueError, match="ORGANIZATION_ID"):
        delivery.TelegramSettings.from_environment()
