from __future__ import annotations

import os
import socket
import threading
import time
from io import BytesIO
from uuid import uuid4

import pytest
import uvicorn
from openpyxl import Workbook

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
        assert page.get_by_role("heading", name="Как работает Agent").is_visible()
        assert page.get_by_role("heading", name="Последний инцидент").is_visible()
        assert page.locator("#setup-guide").is_visible()

        # The compact desktop header (1101–1320px) keeps navigation behind
        # the same menu button as tablet layouts; use the real user path.
        page.locator("#nav-toggle").click()
        page.locator("#agent-credentials-nav").click()
        page.locator("#agent-credentials").scroll_into_view_if_needed()
        page.get_by_role("button", name="Создать ключ для компьютера").click()
        credential_dialog = page.locator("#agent-credential-dialog")
        credential_dialog.wait_for(state="visible")
        agent_username = page.locator("#agent-credential-username").input_value()
        agent_secret = page.locator("#agent-credential-secret").input_value()
        assert agent_username.startswith("ag-")
        assert len(agent_secret) >= 32
        assert page.locator("#agent-credentials-list").get_by_text(agent_username).is_visible()
        credential_dialog.get_by_role("button", name="Я скопировал данные").click()
        credential_dialog.wait_for(state="hidden")
        assert page.locator("#agent-credential-secret").input_value() == ""

        page.set_viewport_size({"width": 1280, "height": 900})
        assert page.locator(".app-header").evaluate("element => element.getBoundingClientRect().height < 220")
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#devices']").click()
        page.locator("#devices").scroll_into_view_if_needed()
        assert page.locator("#show-create").is_visible()

        page.set_viewport_size({"width": 900, "height": 900})
        page.locator("#nav-toggle").click()
        assert page.locator("#main-nav a[href='#devices']").is_visible()
        page.locator("#main-nav a[href='#devices']").click()

        page.locator("#show-create").click()
        form = page.locator("#create-asset")
        form.locator('[name="inventory_number"]').fill(inventory_number)
        form.locator('[name="name"]').fill("Browser E2E workstation")
        form.get_by_role("button", name="Сохранить имущество").click()

        furniture_number = f"E2E-{uuid4().hex[:10]}"
        page.locator("#show-create").click()
        form.locator('[name="inventory_number"]').fill(furniture_number)
        form.locator('[name="name"]').fill("Browser E2E classroom desks")
        form.locator('[name="asset_type"]').select_option("Furniture")
        form.locator('[name="tracking_mode"]').select_option("GROUPED")
        form.locator('[name="quantity"]').fill("12")
        form.get_by_role("button", name="Сохранить имущество").click()
        furniture_row = page.locator("#assets tr", has_text=furniture_number)
        furniture_row.wait_for()
        assert furniture_row.get_by_text("Ручной учёт").is_visible()

        import_workbook = Workbook()
        import_sheet = import_workbook.active
        import_sheet.append(["inventory_number", "name", "asset_type"])
        for index in range(30):
            import_sheet.append([f"PREVIEW-{index:03d}", f"Preview asset {index:03d}", "Desktop"])
        import_stream = BytesIO()
        import_workbook.save(import_stream)
        page.locator("#import-assets-file").set_input_files({
            "name": "preview.xlsx",
            "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            "buffer": import_stream.getvalue(),
        })
        page.locator("#import-preview-dialog").wait_for(state="visible")
        assert page.locator("#import-preview-samples tbody tr").count() == 25
        assert page.locator("#import-preview-page-info").inner_text().startswith("Позиции 1–25 из 30")
        page.locator("#import-preview-next").click()
        assert page.locator("#import-preview-samples tbody tr").count() == 5
        page.locator('[data-import-row="25"]').uncheck()
        assert page.locator("#import-preview-rows").inner_text() == "29"
        page.locator("#cancel-import-preview").click()

        row = page.locator("#assets tr", has_text=inventory_number)
        row.wait_for()
        open_button = row.get_by_role("button", name="Открыть карточку")
        assert open_button.is_visible()
        open_button.click()
        page.locator("#detail-title").filter(has_text="Browser E2E workstation").wait_for()
        assert page.get_by_text("Компьютер пока не связан с Agent").is_visible()
        assert page.get_by_role("heading", name="Состав компьютера").is_hidden()

        api_headers = {"X-AssetGuard-Admin-Token": admin_secret}
        building = page.request.post(f"{base_url}/admin/locations/buildings", headers=api_headers, data={"name": "E2E корпус"}).json()
        floor = page.request.post(f"{base_url}/admin/locations/buildings/{building['id']}/floors", headers=api_headers, data={"name": "2"}).json()
        room = page.request.post(f"{base_url}/admin/locations/floors/{floor['id']}/rooms", headers=api_headers, data={"name": "205", "purpose": "Компьютерный класс", "responsible_name": "E2E ответственный"}).json()
        room_asset = page.request.post(f"{base_url}/admin/assets", headers=api_headers, data={"inventory_number": f"ROOM-{uuid4().hex[:8]}", "name": "Проектор кабинета", "asset_type": "Projector", "room_id": room["id"]})
        assert room_asset.ok
        page.reload()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        page.set_viewport_size({"width": 390, "height": 844})
        page.locator("#devices").scroll_into_view_if_needed()
        assert page.locator("#device-search").is_visible()
        page.locator("#nav-toggle").click()
        assert page.locator("#main-nav a[href='#locations']").is_visible()
        page.locator("#main-nav a[href='#locations']").click()
        room_row = page.locator(".location-room", has_text="каб. 205")
        room_row.get_by_role("button", name="Открыть кабинет").click()
        page.locator("#room-detail-title").filter(has_text="Кабинет 205").wait_for()
        assert page.locator("#room-tab-content").get_by_text("E2E ответственный").is_visible()
        page.locator("#room-edit-action").click()
        page.locator("#room-edit-dialog").wait_for(state="visible")
        page.locator("#room-edit-contact").fill("e2e@example.org")
        page.locator("#room-edit-submit").click()
        page.locator("#room-edit-dialog").wait_for(state="hidden")
        assert page.locator("#room-tab-content").get_by_text("e2e@example.org").is_visible()
        page.locator('[data-room-tab="inventory"]').click()
        assert page.locator("#room-tab-content").get_by_text("Проектор кабинета").is_visible()
        page.locator('[data-room-tab="history"]').click()
        assert page.locator("#room-tab-content").get_by_text("Актив добавлен").is_visible()
        page.locator("#room-vision-action").click()
        assert page.locator("#vision-location-room").input_value() == room["id"]
        assert page.locator("#vision-asset-id option").count() == 2
        assert page.locator("#vision-asset-id option", has_text="Проектор кабинета").count() == 1
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        assert console_errors == []
        browser.close()
