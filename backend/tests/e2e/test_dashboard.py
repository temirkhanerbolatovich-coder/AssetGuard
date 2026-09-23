from __future__ import annotations

import os
import socket
import threading
import time
from uuid import uuid4

import pytest
import uvicorn

from assetguard.app import app


pytestmark = pytest.mark.skipif(
    os.environ.get("ASSETGUARD_RUN_BROWSER_E2E") != "1",
    reason="Set ASSETGUARD_RUN_BROWSER_E2E=1 to run browser tests.",
)


@pytest.fixture
def live_server():
    listener = socket.socket()
    listener.bind(("127.0.0.1", 0))
    listener.listen(128)
    port = listener.getsockname()[1]
    server = uvicorn.Server(uvicorn.Config(app, log_level="warning"))
    thread = threading.Thread(target=server.run, kwargs={"sockets": [listener]}, daemon=True)
    thread.start()
    for _ in range(100):
        if server.started:
            break
        time.sleep(0.05)
    if not server.started:
        raise RuntimeError("Browser E2E server did not start.")
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()


def test_admin_can_open_dashboard_and_create_asset(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url = live_server
    admin_secret = os.environ["ASSETGUARD_ADMIN_SHARED_SECRET"]
    inventory_number = f"E2E-{uuid4().hex[:10]}"

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        console_errors = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(base_url)
        page.locator("#token").fill(admin_secret)
        page.get_by_role("button", name="Войти").click()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()

        page.get_by_role("button", name="Добавить актив").click()
        form = page.locator("#create-asset")
        form.locator('[name="inventory_number"]').fill(inventory_number)
        form.locator('[name="name"]').fill("Browser E2E workstation")
        form.locator('[name="room"]').fill("CI room")
        form.get_by_role("button", name="Создать").click()

        row = page.locator("#assets tr", has_text=inventory_number)
        row.wait_for()
        row.click()
        page.locator("#detail-title").filter(has_text="Browser E2E workstation").wait_for()
        assert page.get_by_role("heading", name="Состав оборудования").is_visible()
        assert page.get_by_role("heading", name="Эталон и изменения").is_visible()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#devices").scroll_into_view_if_needed()
        assert page.locator("#device-search").is_visible()
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        assert console_errors == []
        browser.close()
