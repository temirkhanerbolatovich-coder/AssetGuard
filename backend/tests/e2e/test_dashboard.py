from __future__ import annotations

import os
import json
import socket
import threading
import time
from datetime import UTC, datetime
from io import BytesIO
from pathlib import Path
from uuid import uuid4

import pytest
import uvicorn
from openpyxl import Workbook

from assetguard.app import app
from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session_factory
from assetguard.modules.assets.models import OrganizationRecord


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
        page.locator("#login-mode").click()
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

        reenrolment_computer = f"UNKNOWN-{uuid4().hex[:8]}"
        reenrolment_response = page.request.post(
            f"{base_url}/agent/re-enrolments",
            data={
                "identifier_type": "SMBIOS_UUID",
                "identifier_value": str(uuid4()),
                "computer_name": reenrolment_computer,
                "installer_version": "0.1.7",
            },
        )
        assert reenrolment_response.status == 202
        page.locator("#refresh-agent-reenrolments").click()
        reenrolment_row = page.locator("#agent-reenrolments-list .credential-row", has_text=reenrolment_computer)
        reenrolment_row.wait_for()
        assert reenrolment_row.get_by_text("совпадение не найдено").is_visible()
        assert reenrolment_row.get_by_role("button", name="Подтвердить").count() == 0
        reenrolment_row.get_by_role("button", name="Отклонить").click()
        confirmation_dialog.wait_for(state="visible")
        confirmation_dialog.get_by_role("button", name="Отклонить").click()
        confirmation_dialog.wait_for(state="hidden")
        assert page.locator("#agent-reenrolments-list .credential-row", has_text=reenrolment_computer).get_by_text("Отклонён", exact=True).is_visible()

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
        import_sheet.append(["inventory_number", "name", "asset_type", "quantity", "unit", "tracking_mode"])
        for index in range(30):
            import_sheet.append([f"PREVIEW-{index:03d}", f"Preview asset {index:03d}", "Furniture", 12, "шт.", "GROUPED"])
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
        first_import_row = page.locator("#import-preview-samples tbody tr").first
        assert "12 шт." in first_import_row.inner_text()
        assert "Групповой" in first_import_row.inner_text()
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
            "X-AssetGuard-Source-Version": "1.20",
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
        initial["content"]["tag"] = ["assetguard-installer-0.1.6"]
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
        page.locator("#login-mode").click()
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
        assert page.locator("#device-general").get_by_text("Версия Agent").is_visible()
        assert page.locator("#device-general").get_by_text("1.20", exact=True).is_visible()
        assert page.locator("#device-general").get_by_text("Версия установщика").is_visible()
        assert page.locator("#device-general").get_by_text("0.1.6", exact=True).is_visible()

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
        page.locator("#asset-tab-hardware").wait_for(state="visible")
        assert page.url.endswith(f"#asset={asset_id}&tab=hardware")
        page.go_forward()
        page.locator("#asset-tab-baseline").wait_for(state="visible")

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


def assert_no_page_overflow(page, width):
    layout = page.locator("body").evaluate("""element => ({
        viewport: element.clientWidth,
        width: element.scrollWidth,
        overflow: [...document.querySelectorAll('body *')].filter(node => {
            const rect = node.getBoundingClientRect();
            return rect.width > 0 && rect.right > element.clientWidth + 1;
        }).slice(0, 12).map(node => ({tag: node.tagName, id: node.id, className: node.className, text: node.textContent.slice(0, 90), right: node.getBoundingClientRect().right}))
    })""")
    assert layout["width"] <= layout["viewport"], {"viewport_width": width, "layout": layout}


def test_sign_in_screen_named_account_keyboard_and_mobile(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    settings = get_settings()
    username = f"ui-review-{uuid4().hex[:6]}"
    password = "Browser-test-password-123"
    with get_session_factory()() as session:
        organization = OrganizationRecord(name="Школа · тестовый интерфейс", created_at=datetime.now(UTC))
        session.add(organization)
        session.commit()
        organization_id = str(organization.id)
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(10_000)
        requests = []
        page.on("request", lambda request: requests.append(request.url))
        page.goto(f"{live_server}/#devices")
        assert page.locator("#auth-screen").is_visible()
        assert page.locator("#app-main").is_hidden()
        assert page.locator("#app-header").is_hidden()
        assert not any("/admin/" in url or "/auth/me" in url for url in requests)
        assert page.locator(".skeleton:visible").count() == 0
        preview_dir = Path(__file__).resolve().parents[3] / "outputs/ui-stage1-preview-2026-10-05"
        def capture(name):
            if os.environ.get("ASSETGUARD_CAPTURE_UI_PREVIEWS") == "1":
                preview_dir.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(preview_dir / name), full_page=name.startswith("login"))
        capture("login-desktop.png")
        for width in (320, 360, 390, 768, 1024, 1366, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            assert_no_page_overflow(page, width)
        page.set_viewport_size({"width": 390, "height": 844})
        capture("login-mobile.png")
        page.locator("#login").click()
        assert page.locator("#login-error").is_visible()
        assert page.locator("#login-error").evaluate("element => element === document.activeElement")
        page.locator("#login-error-field").click()
        assert page.locator("#username").evaluate("element => element === document.activeElement")
        created = page.request.post(f"{live_server}/admin/users", headers={"X-AssetGuard-Admin-Token": settings.admin_shared_secret}, data={"username": username, "password": password, "role": "ADMIN", "organization_id": organization_id})
        assert created.status == 201
        page.locator("#username").fill(username)
        page.locator("#token").fill("Incorrect-password-123")
        page.locator("#login").click()
        playwright.expect(page.locator("#login-error-text")).to_contain_text("Неверный логин или пароль")
        assert page.locator("#app-main").is_hidden()
        assert page.evaluate("sessionStorage.getItem('assetguard-admin-token')") is None
        page.locator("#token").fill(password)
        page.locator("#token").press("Enter")
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        assert page.url.endswith("#devices")
        assert page.locator("#devices").is_visible()
        assert page.locator("#session-state").inner_text() == username
        assert page.locator("#session-state").is_visible()
        assert page.locator("#organization-context").inner_text() == "Школа · тестовый интерфейс"
        assert page.locator("#token").input_value() == ""
        assert page.locator("#username").is_hidden()
        page.locator("#nav-toggle").click()
        assert page.locator("#nav-toggle").get_attribute("aria-expanded") == "true"
        page.keyboard.press("Escape")
        assert page.locator("#nav-toggle").get_attribute("aria-expanded") == "false"
        assert page.locator("#nav-toggle").evaluate("element => element === document.activeElement")
        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#overview']").click()
        page.locator("#overview").wait_for(state="visible")
        page.locator("#toast").wait_for(state="hidden")
        for width in (320, 360, 390, 768, 1024, 1366, 1920):
            page.set_viewport_size({"width": width, "height": 900})
            assert_no_page_overflow(page, width)
        page.set_viewport_size({"width": 390, "height": 844})
        capture("workspace-mobile.png")
        page.set_viewport_size({"width": 1366, "height": 900})
        capture("workspace-desktop.png")
        previous_session = page.evaluate("sessionStorage.getItem('assetguard-admin-token')")
        page.locator("#logout").click()
        page.locator("#auth-screen").wait_for(state="visible")
        assert page.locator("#app-header").is_hidden()
        assert page.evaluate("sessionStorage.getItem('assetguard-admin-token')") is None
        # The server must revoke named sessions, not just hide the interface.
        page.wait_for_function("() => document.querySelector('#toast').textContent.includes('вышли')")
        for _ in range(30):
            response = page.request.get(f"{live_server}/auth/me", headers={"X-AssetGuard-Admin-Token": previous_session})
            if response.status == 401:
                break
            page.wait_for_timeout(50)
        assert response.status == 401
        browser.close()


def test_workspace_error_retry_expiry_and_logout_during_loading(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(10_000)
        page.route("**/admin/assets", lambda route: route.fulfill(status=503, json={"detail": "test unavailable"}))
        page.goto(f"{live_server}/#devices")
        page.locator("#login-mode").click()
        page.locator("#token").fill(get_settings().admin_shared_secret)
        page.locator("#login").click()
        page.locator("#retry-load").wait_for(state="visible")
        assert page.locator("#devices").is_hidden()
        assert page.locator("#status").inner_text() == "Данные не обновлены"
        assert "Вход выполнен" not in page.locator("#toast").inner_text()
        page.unroute("**/admin/assets")
        page.locator("#retry-load").click()
        page.locator("#devices").wait_for(state="visible")
        assert page.url.endswith("#devices")
        page.route("**/admin/assets", lambda route: route.fulfill(status=403, json={"detail": "test forbidden"}))
        page.locator("#refresh-data").click()
        page.locator("#retry-load").wait_for(state="visible")
        playwright.expect(page.locator("#feedback-description")).to_contain_text("нет доступа")
        assert page.locator("#devices").is_hidden()
        page.unroute("**/admin/assets")
        page.locator("#retry-load").click()
        page.locator("#devices").wait_for(state="visible")
        page.route("**/auth/me", lambda route: route.fulfill(status=401, json={"detail": "test expired"}))
        page.locator("#refresh-data").click()
        page.locator("#auth-screen").wait_for(state="visible")
        assert page.evaluate("sessionStorage.getItem('assetguard-admin-token')") is None
        assert page.locator("#app-main").is_hidden()
        page.unroute("**/auth/me")
        page.locator("#token").fill(get_settings().admin_shared_secret)
        page.locator("#login").click()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        held = []
        page.route("**/admin/assets", lambda route: held.append(route))
        page.locator("#refresh-data").click()
        page.wait_for_function("() => document.querySelector('#app-main').dataset.loadState === 'loading'")
        page.wait_for_timeout(100)
        assert held
        page.locator("#logout").click()
        page.locator("#auth-screen").wait_for(state="visible")
        assert page.locator("#app-main").is_hidden()
        assert page.locator("#token").input_value() == ""
        assert page.evaluate("sessionStorage.getItem('assetguard-admin-token')") is None
        page.wait_for_timeout(100)
        assert page.locator("#app-main").is_hidden()
        browser.close()


def test_cached_session_timeout_has_retry_and_no_infinite_loading(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(10_000)
        page.clock.install()
        page.add_init_script("sessionStorage.setItem('assetguard-admin-token', 'test-stored-expired-session')")
        held = []
        page.route("**/auth/me", lambda route: held.append(route))
        page.goto(f"{live_server}/#locations")
        assert page.locator("#token").input_value() == ""
        assert page.locator("#app-main").is_hidden()
        assert held
        page.clock.fast_forward(21_000)
        playwright.expect(page.locator("#login-error-text")).to_contain_text("20 секунд")
        assert page.locator("#retry-session").is_visible()
        assert page.locator("#login").is_enabled()
        assert page.url.endswith("#locations")
        page.unroute("**/auth/me")
        page.locator("#retry-session").click()
        playwright.expect(page.locator("#login-error-text")).to_contain_text("недействительны")
        assert page.evaluate("sessionStorage.getItem('assetguard-admin-token')") is None
        browser.close()


def test_late_asset_response_does_not_replace_new_route(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(10_000)
        headers = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
        created = page.request.post(f"{live_server}/admin/assets", headers=headers, data={"inventory_number": f"LATE-{uuid4().hex[:8]}", "name": "Отложенная карточка", "asset_type": "Furniture"})
        assert created.status == 201
        asset_id = created.json()["id"]
        detail = page.request.get(f"{live_server}/admin/assets/{asset_id}", headers=headers).json()
        held = []
        page.route(f"**/admin/assets/{asset_id}", lambda route: held.append(route))
        page.goto(f"{live_server}/#asset={asset_id}")
        page.locator("#login-mode").click()
        page.locator("#token").fill(get_settings().admin_shared_secret)
        page.locator("#login").click()
        page.locator("#detail-title").filter(has_text="Загрузка").wait_for()
        assert held
        page.locator("#main-nav a[href='#overview']").click()
        page.locator("#overview").wait_for(state="visible")
        held[0].fulfill(status=200, json=detail)
        page.wait_for_timeout(100)
        assert page.url.endswith("#overview")
        assert page.locator("#detail").is_hidden()
        assert page.get_by_role("heading", name="Центр контроля", exact=True).is_visible()
        browser.close()


def test_registry_pages_and_unified_physical_incident_workflow(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    settings = get_settings()
    headers = {"X-AssetGuard-Admin-Token": settings.admin_shared_secret}
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(10_000)
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))
        def post(path, data):
            response = page.request.post(live_server + path, headers=headers, data=data)
            assert response.ok, response.text()
            return response.json()
        room_ids = []
        for name in ("North", "South"):
            building = post("/admin/locations/buildings", {"name": name})
            floor = post(f"/admin/locations/buildings/{building['id']}/floors", {"name": "1"})
            room_ids.append(post(f"/admin/locations/floors/{floor['id']}/rooms", {"name": "101"})["id"])
        assets = [post("/admin/assets", {"inventory_number": f"DESK-{index:02d}", "name": f"Desk {index:02d}",
            "asset_type": "Furniture", "category": "FURNITURE", "tracking_mode": "GROUPED", "quantity": 3, "unit": "шт.",
            "room_id": room_ids[index // 22]}) for index in range(44)]
        for index in (0, 22):
            room_assets = assets[index:index+22]
            post(f"/admin/locations/rooms/{room_ids[index//22]}/inspections", {"comment": "Controlled inspection",
                "items": [{"asset_id": asset["id"], "result": "MISSING" if asset == room_assets[0] else "PRESENT",
                    "affected_quantity": 2 if asset == room_assets[0] else 0, "comment": "Two desks absent" if asset == room_assets[0] else ""} for asset in room_assets]})
        post("/admin/assets", {"inventory_number": "PRINTER", "name": "Printer no Agent", "asset_type": "Printer", "room_id": room_ids[0]})
        physical = page.request.get(live_server + "/admin/locations/physical-incidents", headers=headers).json()
        incident = next(item for item in physical if item["asset_id"] == assets[0]["id"])
        initial = json.loads((FIXTURES / "glpi-agent-minimal-sanitized.json").read_text(encoding="utf-8"))
        unique = uuid4().hex
        initial["deviceid"] = unique
        initial["content"]["hardware"]["uuid"] = unique
        inventory_headers = {"X-AssetGuard-Ingest-Token": settings.inventory_shared_secret,
            "X-AssetGuard-Idempotency-Key": uuid4().hex, "X-AssetGuard-Source": "GLPI_AGENT",
            "X-AssetGuard-Source-Version": "1.20", "X-AssetGuard-Schema-Version": "ui-stage2", "X-AssetGuard-Inventory-Type": "FULL"}
        first = page.request.post(live_server + "/internal/inventories", headers=inventory_headers, data=initial)
        assert first.ok
        snapshot_id = first.json()["snapshot_id"]
        endpoint_id = page.request.get(f"{live_server}/admin/snapshots/{snapshot_id}", headers=headers).json()["endpoint_id"]
        computer = post("/admin/assets", {"inventory_number": "PC", "name": "Computer Agent", "asset_type": "Desktop", "room_id": room_ids[0]})
        post(f"/admin/endpoints/{endpoint_id}/asset/{computer['id']}", {})
        post(f"/admin/snapshots/{snapshot_id}/baseline", {"reason": "Controlled baseline"})
        removed = json.loads((FIXTURES / "glpi-agent-hardware-ram-removed.json").read_text(encoding="utf-8"))
        removed["deviceid"] = unique
        removed["content"]["hardware"]["uuid"] = unique
        inventory_headers["X-AssetGuard-Idempotency-Key"] = uuid4().hex
        assert page.request.post(live_server + "/internal/inventories", headers=inventory_headers, data=removed).ok

        page.goto(live_server + "/#devices")
        page.locator("#login-mode").click()
        page.locator("#token").fill(settings.admin_shared_secret)
        page.locator("#login").click()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        def capture(name):
            if os.environ.get("ASSETGUARD_CAPTURE_UI_PREVIEWS") == "1":
                output = Path(__file__).resolve().parents[3] / "outputs/ui-stage2-preview-2026-10-05"
                output.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(output / name))
        capture("registry-desktop.png")
        for width in (320, 390, 768, 1366):
            page.set_viewport_size({"width": width, "height": 900})
            assert_no_page_overflow(page, width)
            if width == 390: capture("registry-mobile.png")
        assert page.locator("#assets tr.device-row").count() == 20
        page.locator("#devices .device-filters summary").click()
        page.locator("#device-category-filter").select_option("FURNITURE")
        page.locator("#device-search").fill("Desk")
        page.locator("#device-sort").select_option("name")
        assert "из 44" in page.locator("#device-result-count").inner_text()
        page.locator("#device-pagination").get_by_role("button", name="Следующая").click()
        assert page.locator("#device-pagination").get_by_text("Страница 2 из 3").is_visible()
        page.locator("#assets .device-open-link", has_text="Desk 20").click()
        page.locator("#detail-title").filter(has_text="Desk 20").wait_for()
        assert page.get_by_role("tab", name="Оборудование", exact=True).is_hidden()
        assert page.locator("#detail-status").get_by_text("Ручной учёт").is_visible()
        page.locator("#detail-back").click()
        page.locator("#devices").wait_for(state="visible")
        assert page.locator("#device-search").input_value() == "Desk"
        assert page.locator("#device-pagination").get_by_text("Страница 2 из 3").is_visible()
        page.locator("#device-room-filter").select_option(room_ids[1])
        assert "из 22" in page.locator("#device-result-count").inner_text()
        assert page.locator("#device-pagination").get_by_text("Страница 1 из 2").is_visible()
        page.locator("#clear-device-filters").click()
        assert page.locator("#device-sort").input_value() == "recent"
        page.locator("#device-search").fill("PRINTER")
        assert page.locator("#assets").get_by_text("Ручной учёт", exact=True).is_visible()

        page.locator("#main-nav a[href='#incidents']").click()
        assert page.locator("#incident-center-list").get_by_text("Agent · технический", exact=False).count() > 0
        assert page.locator("#incident-center-list").get_by_text("Обход · физический", exact=False).count() == 2
        capture("incidents-desktop.png")
        for width in (320, 390, 768, 1366):
            page.set_viewport_size({"width": width, "height": 900})
            assert_no_page_overflow(page, width)
            if width == 390: capture("incidents-mobile.png")
        page.locator(".incident-filters summary").click()
        page.locator("#incident-type-filter").select_option("PHYSICAL")
        page.locator("#incident-room-filter").select_option(room_ids[0])
        assert page.locator("#incident-center-list .incident-card").count() == 1
        page.locator("#incident-date-from").fill("2099-12-31")
        page.locator("#incident-date-to").fill("2000-01-01")
        assert page.locator("#incident-filter-error").is_visible()
        page.locator("#incident-date-from").fill("")
        page.locator("#incident-date-to").fill("")
        page.locator("#incident-center-list .open-physical-incident").click()
        page.locator("#incident-detail-title").filter(has_text="Desk 00").wait_for()
        assert page.url.endswith(f"#physical-incident={incident['id']}")
        assert page.locator("#incident-detail-comparison").get_by_text("Two desks absent", exact=True).is_visible()
        assert "Two desks absent" in page.locator("#incident-detail-evidence").text_content()
        capture("physical-incident-desktop.png")
        page.locator("#incident-detail-back").click()
        page.locator("#incidents").wait_for(state="visible")
        assert page.locator("#incident-type-filter").input_value() == "PHYSICAL"
        assert page.locator("#incident-room-filter").input_value() == room_ids[0]
        page.locator("#incident-center-list .open-physical-incident").click()
        page.locator("#physical-detail-decision").wait_for()
        page.reload()
        page.locator("#physical-detail-decision").wait_for()
        for width in (320, 390, 768, 1366):
            page.set_viewport_size({"width": width, "height": 900})
            assert_no_page_overflow(page, width)
        page.locator("#physical-detail-decision").click()
        page.locator("#physical-incident-dialog").wait_for(state="visible")
        page.locator("#physical-incident-action-select").select_option("WRITE_OFF")
        page.locator("#physical-incident-quantity").fill("1")
        page.locator("#physical-incident-comment").fill("Approved damaged unit disposal")
        page.locator("#physical-incident-document-number").fill("UI-STAGE2-ACT")
        page.locator("#physical-incident-submit").click()
        page.locator("#physical-incident-dialog").wait_for(state="hidden")
        page.locator("#incident-detail-decisions").get_by_text("UI-STAGE2-ACT", exact=False).wait_for()
        assert page.url.endswith(f"#physical-incident={incident['id']}")
        detail = page.request.get(f"{live_server}/admin/assets/{assets[0]['id']}", headers=headers).json()
        assert detail["quantity"] == 2
        physical_detail = page.request.get(f"{live_server}/admin/locations/physical-incidents/{incident['id']}", headers=headers).json()
        assert len(physical_detail["decisions"]) == 1
        assert page.request.get(f"{live_server}/admin/locations/physical-incidents/{incident['id']}/act.pdf", headers=headers).status == 200
        page.locator("#incident-detail-back").click()
        page.locator("#incidents").wait_for(state="visible")
        if not page.locator(".incident-filters").evaluate("element => element.open"):
            page.locator(".incident-filters summary").click()
        page.locator("#clear-incident-filters").click()
        page.locator("#incident-status-filter").select_option("RESOLVED")
        assert page.locator("#incident-center-list .incident-card").count() == 1
        assert failures == [], failures
        browser.close()
