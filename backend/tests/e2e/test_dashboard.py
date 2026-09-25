from __future__ import annotations

import os
import json
import socket
import threading
import time
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
from openpyxl import Workbook

from assetguard.app import app
from assetguard.infrastructure.config import get_settings


FIXTURES = Path(__file__).parents[1] / "fixtures"


pytestmark = pytest.mark.skipif(
    os.environ.get("ASSETGUARD_RUN_BROWSER_E2E") != "1",
    reason="Set ASSETGUARD_RUN_BROWSER_E2E=1 to run browser tests.",
)


@pytest.fixture
def live_server():
    original_rate_limit = os.environ.get("ASSETGUARD_RATE_LIMIT_PER_MINUTE")
    os.environ["ASSETGUARD_RATE_LIMIT_PER_MINUTE"] = "1000"
    get_settings.cache_clear()
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
    middleware = app.middleware_stack
    while middleware is not None:
        if hasattr(middleware, "_requests"):
            middleware._requests.clear()
            break
        middleware = getattr(middleware, "app", None)
    try:
        yield f"http://127.0.0.1:{port}"
    finally:
        server.should_exit = True
        thread.join(timeout=10)
        listener.close()
        if original_rate_limit is None:
            os.environ.pop("ASSETGUARD_RATE_LIMIT_PER_MINUTE", None)
        else:
            os.environ["ASSETGUARD_RATE_LIMIT_PER_MINUTE"] = original_rate_limit
        get_settings.cache_clear()


def test_admin_can_open_dashboard_and_create_asset(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url = live_server
    admin_secret = os.environ["ASSETGUARD_ADMIN_SHARED_SECRET"]
    inventory_number = f"E2E-{uuid4().hex[:10]}"
    room_name = f"205-{uuid4().hex[:6]}"
    ui_building_name = f"UI корпус {uuid4().hex[:6]}"
    ui_floor_name = "3"
    ui_room_name = f"301-{uuid4().hex[:4]}"

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(10_000)
        console_errors = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)
        page.goto(base_url)
        page.locator("#token").fill(admin_secret)
        page.get_by_role("button", name="Войти").click()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        assert page.get_by_role("heading", name="Центр контроля", exact=True).is_visible()
        assert page.get_by_role("heading", name="Последний инцидент").is_visible()
        assert page.locator("#setup-guide").is_visible()

        for viewport in ({"width": 1920, "height": 1080}, {"width": 1366, "height": 768}, {"width": 768, "height": 900}):
            page.set_viewport_size(viewport)
            assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        assert page.locator("#nav-toggle").is_visible()

        # Desktop uses a persistent application sidebar and one visible route.
        page.set_viewport_size({"width": 1280, "height": 900})
        sidebar_width = page.locator(".app-header").evaluate("element => element.getBoundingClientRect().width")
        assert 250 <= sidebar_width <= 280
        assert page.locator("#overview").is_visible()
        assert page.locator("#devices").is_hidden()
        page.locator("#main-nav a[href='#incidents']").click()
        page.locator("#incidents").wait_for(state="visible")
        assert page.locator("#incidents").get_by_role("heading", name="Инциденты", exact=True).is_visible()
        page.go_back()
        page.locator("#overview").wait_for(state="visible")

        page.locator("#agent-credentials-nav").click()
        page.locator("#agent-credentials").wait_for(state="visible")
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
        credential_row = page.locator("#agent-credentials-list .credential-row", has_text=agent_username)
        credential_row.get_by_role("button", name="Отозвать ключ").click()
        confirmation_dialog = page.locator("#confirmation-dialog")
        confirmation_dialog.wait_for(state="visible")
        confirmation_dialog.get_by_role("button", name="Отозвать ключ").click()
        confirmation_dialog.wait_for(state="hidden")
        assert page.locator("#agent-credentials-list .credential-row", has_text=agent_username).get_by_text("Отозван", exact=True).is_visible()

        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        page.locator("#main-nav a[href='#devices']").click()
        page.locator("#devices").wait_for(state="visible")
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

        page.locator("#data-exchange-shortcut").click()
        page.locator("#data-exchange").wait_for(state="visible")
        assert page.url.endswith("#data-exchange")
        assert page.locator("#devices").is_hidden()
        assert page.locator("#data-exchange").get_by_role("heading", name="Импорт и экспорт", exact=True).is_visible()

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
        assert "preview.xlsx" in page.locator("#import-preview-file").inner_text()
        assert "КБ" in page.locator("#import-preview-file").inner_text()
        assert page.locator("#import-assets").is_disabled()
        assert page.locator("#import-preview-samples tbody tr").count() == 25
        assert page.locator("#import-preview-page-info").inner_text().startswith("Позиции 1–25 из 30")
        page.locator("#import-preview-next").click()
        assert page.locator("#import-preview-samples tbody tr").count() == 5
        page.locator('[data-import-row="25"]').uncheck()
        assert page.locator("#import-preview-rows").inner_text() == "29"
        page.locator("#cancel-import-preview").click()
        page.locator("#data-exchange-status").filter(has_text="Реестр не изменён").wait_for()
        page.get_by_role("link", name="Вернуться к устройствам").click()
        page.locator("#devices").wait_for(state="visible")

        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#locations']").click()
        page.locator("#locations").wait_for(state="visible")
        page.locator("#create-building [name='name']").fill(ui_building_name)
        page.locator("#create-building").get_by_role("button", name="Добавить корпус").click()
        ui_building = page.locator("#location-tree .attention-item", has_text=ui_building_name).first
        ui_building.wait_for()
        ui_building.get_by_role("button", name="+ этаж").click()
        location_dialog = page.locator("#location-create-dialog")
        location_dialog.wait_for(state="visible")
        assert location_dialog.get_by_role("heading", name="Добавить этаж").is_visible()
        page.locator("#location-create-name").fill(ui_floor_name)
        page.locator("#location-create-submit").click()
        location_dialog.wait_for(state="hidden")
        ui_building.get_by_text(f"Этаж {ui_floor_name}", exact=True).wait_for()
        ui_building.get_by_role("button", name="+ кабинет").click()
        location_dialog.wait_for(state="visible")
        page.locator("#location-create-name").fill(ui_room_name)
        page.locator("#location-create-submit").click()
        location_dialog.wait_for(state="hidden")
        ui_building.get_by_text(f"каб. {ui_room_name}", exact=False).wait_for()

        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#devices']").click()
        page.locator("#devices").wait_for(state="visible")
        row = page.locator("#assets tr", has_text=inventory_number)
        row.wait_for()
        open_button = row.get_by_role("button", name="Открыть карточку")
        assert open_button.is_visible()
        open_button.click()
        assert page.url.endswith(f"#asset={row.get_attribute('data-asset-id')}")
        page.locator("#detail-title").filter(has_text="Browser E2E workstation").wait_for()
        assert page.get_by_text("Компьютер пока не связан с Agent").is_visible()
        assert page.get_by_role("heading", name="Состав компьютера").is_hidden()
        assert page.get_by_role("tab", name="Оборудование").is_hidden()
        assert page.get_by_role("tab", name="Эталон и изменения").is_hidden()
        assert page.get_by_role("tab", name="Технические данные").is_hidden()
        assert page.get_by_role("tab", name="Обзор").get_attribute("aria-selected") == "true"
        page.locator("#edit-asset").click()
        page.locator("#asset-edit-dialog").wait_for(state="visible")
        page.locator("#asset-edit-name").fill("Browser E2E workstation updated")
        page.locator("#asset-edit-submit").click()
        page.locator("#asset-edit-dialog").wait_for(state="hidden")
        page.locator("#detail-title").filter(has_text="Browser E2E workstation updated").wait_for()
        page.locator("#show-asset-qr").click()
        page.locator("#asset-qr-dialog").wait_for(state="visible")
        assert page.locator("#asset-qr-public-url").evaluate("element => document.activeElement === element")
        page.locator("#asset-qr-public-url").press("Shift+Tab")
        assert page.locator("#asset-qr-submit").evaluate("element => document.activeElement === element")
        page.locator("#asset-qr-dialog").press("Escape")
        page.locator("#asset-qr-dialog").wait_for(state="hidden")
        assert page.locator("#show-asset-qr").evaluate("element => document.activeElement === element")

        page.set_viewport_size({"width": 360, "height": 800})
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        page.locator("#show-asset-qr").click()
        page.locator("#asset-qr-dialog").wait_for(state="visible")
        assert page.locator("#asset-qr-dialog").evaluate("element => { const box = element.getBoundingClientRect(); return box.width <= innerWidth && box.height <= innerHeight; }")
        page.locator("#asset-qr-dialog").press("Escape")
        page.locator("#asset-qr-dialog").wait_for(state="hidden")
        page.set_viewport_size({"width": 1280, "height": 900})

        api_headers = {"X-AssetGuard-Admin-Token": admin_secret}
        building = page.request.post(f"{base_url}/admin/locations/buildings", headers=api_headers, data={"name": "E2E корпус"}).json()
        floor = page.request.post(f"{base_url}/admin/locations/buildings/{building['id']}/floors", headers=api_headers, data={"name": "2"}).json()
        room = page.request.post(f"{base_url}/admin/locations/floors/{floor['id']}/rooms", headers=api_headers, data={"name": room_name, "purpose": "Компьютерный класс", "responsible_name": "E2E ответственный"}).json()
        room_asset = page.request.post(f"{base_url}/admin/assets", headers=api_headers, data={"inventory_number": f"ROOM-{uuid4().hex[:8]}", "name": "Проектор кабинета", "asset_type": "Projector", "room_id": room["id"]})
        assert room_asset.ok
        page.reload()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        assert page.locator("#detail").is_visible()
        page.locator("#detail-back").click()
        page.locator("#devices").wait_for(state="visible")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#device-search").is_visible()
        page.locator("#nav-toggle").click()
        assert page.locator("#main-nav a[href='#locations']").is_visible()
        page.locator("#main-nav a[href='#incidents']").click()
        assert page.locator("#nav-toggle").get_attribute("aria-expanded") == "false"
        assert page.locator("#nav-toggle").get_attribute("aria-label") == "Открыть меню"
        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#locations']").click()
        room_row = page.locator(".location-room", has_text=f"каб. {room_name}")
        room_row.get_by_role("button", name="Открыть кабинет").click()
        page.locator("#room-detail-title").filter(has_text=f"Кабинет {room_name}").wait_for()
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
        page.locator("#room-inspection-action").click()
        page.locator("#room-inspection-dialog").wait_for(state="visible")
        page.locator("#room-inspection-items .inspection-result-input").select_option("DAMAGED")
        page.locator("#room-inspection-items .inspection-affected-input").fill("1")
        page.locator("#room-inspection-comment").fill("E2E обход кабинета")
        page.locator("#room-inspection-submit").click()
        page.locator("#room-inspection-dialog").wait_for(state="hidden")
        assert page.locator("#room-tab-content").get_by_text("E2E обход кабинета").is_visible()
        assert page.locator("#room-tab-content").get_by_text("Повреждено · 1").is_visible()
        page.locator('[data-room-tab="incidents"]').click()
        assert page.locator("#room-tab-content").get_by_text("Проектор кабинета: повреждено").is_visible()
        page.locator("#room-tab-content .physical-incident-action").click()
        page.locator("#physical-incident-action-select").select_option("REPAIR")
        page.locator("#physical-incident-comment").fill("Передать проектор в ремонт")
        page.locator("#physical-incident-submit").click()
        page.locator("#physical-incident-dialog").wait_for(state="hidden")
        assert page.locator("#room-tab-content").get_by_text("Ремонт").is_visible()
        page.locator("#room-vision-action").click()
        assert page.locator("#vision-location-room").input_value() == room["id"]
        assert page.locator("#vision-asset-id option").count() == 2
        assert page.locator("#vision-asset-id option", has_text="Проектор кабинета").count() == 1
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        page.locator("#logout").click()
        assert page.locator("#logout").is_hidden()
        assert page.locator("#login").is_visible()
        assert page.locator("#detail").is_hidden()
        assert page.get_by_text("Войдите в AssetGuard", exact=True).is_visible()
        assert console_errors == []
        browser.close()


def test_incident_detail_supports_direct_link_and_managed_decision(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    base_url = live_server
    settings = get_settings()
    unique = uuid4().hex[:10]
    device_id = f"incident-e2e-{unique}"
    hardware_uuid = f"incident-hardware-{unique}"
    inventory_number = f"INC-{unique}"
    admin_headers = {"X-AssetGuard-Admin-Token": settings.admin_shared_secret}

    def inventory_headers():
        return {
            "X-AssetGuard-Ingest-Token": settings.inventory_shared_secret,
            "X-AssetGuard-Idempotency-Key": uuid4().hex,
            "X-AssetGuard-Source": "GLPI_AGENT",
            "X-AssetGuard-Source-Version": "1.19",
            "X-AssetGuard-Schema-Version": "browser-e2e-v1",
            "X-AssetGuard-Inventory-Type": "FULL",
        }

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={"width": 1280, "height": 900})
        console_errors = []
        page.on("console", lambda message: console_errors.append(message.text) if message.type == "error" else None)

        initial = json.loads((FIXTURES / "glpi-agent-minimal-sanitized.json").read_text(encoding="utf-8"))
        initial["deviceid"] = device_id
        initial["content"]["hardware"]["uuid"] = hardware_uuid
        initial["content"]["networks"][0]["macaddr"] = f"02:00:{unique[0:2]}:{unique[2:4]}:{unique[4:6]}:{unique[6:8]}"
        first = page.request.post(f"{base_url}/internal/inventories", headers=inventory_headers(), data=initial)
        assert first.ok
        snapshot_id = first.json()["snapshot_id"]
        snapshot = page.request.get(f"{base_url}/admin/snapshots/{snapshot_id}", headers=admin_headers).json()
        endpoint_id = snapshot["endpoint_id"]
        asset = page.request.post(f"{base_url}/admin/assets", headers=admin_headers, data={
            "inventory_number": inventory_number, "name": "Incident E2E workstation", "asset_type": "Desktop",
        })
        assert asset.ok
        asset_id = asset.json()["id"]
        assert page.request.post(f"{base_url}/admin/endpoints/{endpoint_id}/asset/{asset_id}", headers=admin_headers).ok
        assert page.request.post(f"{base_url}/admin/snapshots/{snapshot_id}/baseline", headers=admin_headers, data={"reason": "Incident browser baseline"}).ok

        removed = json.loads((FIXTURES / "glpi-agent-hardware-ram-removed.json").read_text(encoding="utf-8"))
        removed["deviceid"] = device_id
        removed["content"]["hardware"]["uuid"] = hardware_uuid
        assert page.request.post(f"{base_url}/internal/inventories", headers=inventory_headers(), data=removed).ok
        incidents = page.request.get(f"{base_url}/admin/incidents?endpoint_id={endpoint_id}", headers=admin_headers).json()
        incident = next(item for item in incidents if item["status"] == "OPEN")

        page.goto(f"{base_url}/#incident={incident['id']}")
        page.locator("#token").fill(settings.admin_shared_secret)
        page.get_by_role("button", name="Войти").click()
        page.locator("#incident-detail-title").filter(has_text="Оперативная память").wait_for()
        assert page.locator("#incident-detail").is_visible()
        assert page.locator("#incident-detail-comparison").get_by_text("Было").is_visible()
        assert "RAM-FIXTURE-B" in page.locator("#incident-detail-evidence").text_content()

        page.reload()
        page.locator("#incident-detail-title").filter(has_text="Оперативная память").wait_for()
        assert page.url.endswith(f"#incident={incident['id']}")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        page.locator("#incident-detail-resolve").click()
        dialog = page.locator("#incident-decision-dialog")
        dialog.wait_for(state="visible")
        page.locator("#incident-decision-classification").select_option("AUTHORIZED_CHANGE")
        page.locator("#incident-decision-comment").fill("Плановая замена модуля подтверждена")
        page.locator("#incident-decision-submit").click()
        dialog.wait_for(state="hidden")
        page.locator("#incident-detail-status").get_by_text("Закрыто").wait_for()
        assert page.locator("#incident-detail-decisions").get_by_text("Плановая замена модуля подтверждена").is_visible()
        page.locator("#incident-device-action").get_by_role("button", name="Открыть карточку устройства").click()
        page.locator("#detail-title").filter(has_text="Incident E2E workstation").wait_for()

        asset_detail_requests = []
        page.on(
            "request",
            lambda request: asset_detail_requests.append(request.url)
            if request.method == "GET" and request.url.split("?", 1)[0].endswith(f"/admin/assets/{asset_id}")
            else None,
        )
        page.goto(f"{base_url}/#incidents")
        page.locator("#incidents").wait_for(state="visible")
        page.goto(f"{base_url}/#asset={asset_id}&tab=baseline")
        page.locator("#asset-tab-baseline").wait_for(state="visible")
        assert asset_detail_requests == []

        hardware_tab = page.get_by_role("tab", name="Оборудование")
        baseline_tab = page.get_by_role("tab", name="Эталон и изменения")
        technical_tab = page.get_by_role("tab", name="Технические данные")
        assert hardware_tab.is_visible()
        assert technical_tab.is_visible()
        hardware_tab.click()
        assert page.url.endswith(f"#asset={asset_id}&tab=hardware")
        assert page.locator("#asset-tab-hardware").is_visible()
        baseline_tab.click()
        assert page.url.endswith(f"#asset={asset_id}&tab=baseline")
        assert page.locator("#asset-tab-baseline").is_visible()

        page.reload()
        page.locator("#detail-title").filter(has_text="Incident E2E workstation").wait_for()
        assert page.locator("#asset-tab-baseline").is_visible()
        page.go_back()
        assert page.locator("#asset-tab-hardware").is_visible()
        assert page.url.endswith(f"#asset={asset_id}&tab=hardware")
        page.go_forward()
        assert page.locator("#asset-tab-baseline").is_visible()

        technical_tab = page.get_by_role("tab", name="Технические данные")
        technical_tab.click()
        assert page.url.endswith(f"#asset={asset_id}&tab=technical")
        assert page.locator("#asset-tab-technical").is_visible()
        technical_tab.press("Home")
        assert page.get_by_role("tab", name="Обзор").get_attribute("aria-selected") == "true"
        baseline_tab = page.get_by_role("tab", name="Эталон и изменения")
        baseline_tab.click()
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        page.locator("#accept-baseline").click()
        confirmation = page.locator("#confirmation-dialog")
        confirmation.wait_for(state="visible")
        assert page.locator("#confirmation-reason").get_attribute("required") is not None
        page.locator("#confirmation-reason").fill("Согласованная замена модуля")
        page.locator("#confirmation-submit").click()
        confirmation.wait_for(state="hidden")
        assert page.locator("#baseline-summary").get_by_text("Согласованная замена модуля").is_visible()
        assert console_errors == []
        browser.close()
