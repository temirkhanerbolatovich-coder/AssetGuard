from __future__ import annotations

import os
import json
import socket
import threading
import time
from datetime import UTC, datetime, timedelta
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
from assetguard.modules.notifications.models import TelegramNotificationRecord
from assetguard.modules.snapshots.models import ManagedEndpointRecord


FIXTURES = Path(__file__).parents[1] / "fixtures"


def capture_redesign_preview(page, name):
    output = os.environ.get("ASSETGUARD_REDESIGN_PREVIEW_DIR")
    if output:
        directory = Path(output)
        directory.mkdir(parents=True, exist_ok=True)
        page.locator("#toast").evaluate("element => { element.hidden = true; }")
        page.evaluate("Promise.all(document.getAnimations().filter(animation=>animation.effect.getComputedTiming().iterations!==Infinity).map(animation=>animation.finished.catch(()=>{})))")
        page.screenshot(path=str(directory / name))


pytestmark = pytest.mark.skipif(
    os.environ.get("ASSETGUARD_RUN_BROWSER_E2E") != "1",
    reason="Set ASSETGUARD_RUN_BROWSER_E2E=1 to run browser tests.",
)


def test_agent_fleet_delivery_and_admin_forms_recover_safely(live_server):
    """Exercise real local writes, queue reads, retries, one-time keys and re-enrolment."""
    import base64
    playwright = pytest.importorskip("playwright.sync_api")
    now = datetime.now(UTC)
    with get_session_factory()() as session:
        organization = OrganizationRecord(name="Browser school", created_at=now)
        session.add(organization)
        session.flush()
        for index in range(23):
            session.add(ManagedEndpointRecord(source="TEST", organization_id=organization.id,
                hostname=f"Browser-PC-{index:02d}", status="ONLINE",
                last_seen_at=now-timedelta(hours=30) if index else now,
                created_at=now, updated_at=now))
        for index in range(26):
            session.add(TelegramNotificationRecord(event_key=f"browser-event-{index}",
                organization_id=organization.id, room_id=None, payload={"subject":"never-show-private-body"},
                status="SENT" if index==0 else "PENDING", attempts=1 if index<2 else 0,
                created_at=now, next_attempt_at=now, sent_at=now if index==0 else None,
                last_error_code="HTTP_429" if index==1 else None))
        session.commit()
    with playwright.sync_playwright() as runtime:
        browser=runtime.chromium.launch()
        context=browser.new_context(viewport={"width":1366,"height":900}, permissions=["clipboard-read","clipboard-write"])
        page=context.new_page()
        page.set_default_timeout(10_000)
        errors=[]
        page.on("pageerror",lambda error:errors.append(str(error)))
        page.goto(live_server)
        page.locator("#login-mode").click()
        page.locator("#token").fill(os.environ["ASSETGUARD_ADMIN_SHARED_SECRET"])
        page.get_by_role("button",name="Войти",exact=True).click()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        page.evaluate("location.hash='agent-credentials'")
        page.locator('[data-admin-view="notifications"]').click()
        page.locator("#notification-summary").filter(has_text="принято Telegram: 1").wait_for()
        page.locator('[data-admin-view="fleet"]').click()
        assert "24 ч." in page.locator("#agent-freshness-help").inner_text()
        assert page.locator("#agent-fleet-list .admin-record").count()==20
        page.locator("#agent-status-filter").select_option("STALE")
        assert "Найдено 22 из 23" in page.locator("#agent-fleet-summary").inner_text()
        page.locator("#agent-page-next").click()
        assert page.locator("#agent-fleet-list .admin-record").count()==2
        page.locator("#agent-search").fill("PC-01")
        assert page.locator("#agent-fleet-list .admin-record").count()==1
        assert "Нет свежей инвентаризации" in page.locator("#agent-fleet-list").inner_text()
        page.locator("#agent-search").fill("")
        page.locator("#agent-status-filter").select_option("")
        page.locator("#agent-search").fill("NO-SUCH-COMPUTER")
        page.locator("#agent-fleet-list").get_by_text("Компьютеры не найдены", exact=True).wait_for()
        page.locator("#agent-fleet-list").get_by_role("button", name="Сбросить фильтры").click()
        assert page.locator("#agent-fleet-list .admin-record").count()==20
        assert page.locator('[data-admin-view="fleet"]').get_attribute("aria-selected") == "true"
        page.locator('[data-admin-view="fleet"]').press("ArrowRight")
        assert page.locator('[data-admin-view="connect"]').get_attribute("aria-selected") == "true"
        page.locator('[data-admin-view="notifications"]').click()
        assert page.locator("#notification-list .admin-record").count()==20
        page.locator("#notification-next").click()
        playwright.expect(page.locator("#notification-list .admin-record")).to_have_count(6)
        page.locator("#notification-status-filter").select_option("RETRYING")
        page.locator("#notification-list").get_by_text("Причина: HTTP_429",exact=True).wait_for()
        assert "never-show-private-body" not in page.content()
        page.route("**/admin/notifications?*",lambda route:route.fulfill(status=503,json={"detail":"Delivery temporarily unavailable"}))
        page.locator("#refresh-notifications").click()
        page.locator("#notification-load-error").wait_for(state="visible")
        assert page.locator("#notification-list .admin-record").count()==0
        page.unroute("**/admin/notifications?*")
        page.locator("#refresh-notifications").click()
        page.locator("#notification-list .admin-record").wait_for()
        page.route("**/admin/notifications?*status=SENT",lambda route:route.fulfill(json={"summary":{"pending":24,"retrying":1,"sent":1},"total":0,"limit":20,"offset":0,"items":[]}))
        page.locator("#notification-status-filter").select_option("SENT")
        page.locator("#notification-list").get_by_text("Уведомления не найдены",exact=True).wait_for()
        page.unroute("**/admin/notifications?*status=SENT")
        page.locator("#notification-list").get_by_role("button",name="Показать все").click()
        playwright.expect(page.locator("#notification-list .admin-record")).to_have_count(20)

        def capture(name):
            capture_redesign_preview(page, name)
        page.locator('[data-admin-view="fleet"]').click()
        for width in (1366,1024,768,390,320):
            page.set_viewport_size({"width":width,"height":900})
            assert page.locator("body").evaluate("element=>element.scrollWidth<=element.clientWidth"),width
            page.evaluate("window.scrollTo(0,0)")
            if width in (1366,390): capture(f"agent-{'desktop' if width==1366 else 'mobile'}.png")
        for width in (1366,390):
            page.set_viewport_size({"width":width,"height":900})
            page.locator('[data-admin-view="notifications"]').click()
            capture(f"delivery-{'desktop' if width==1366 else 'mobile'}.png")
        page.set_viewport_size({"width":1366,"height":900})
        page.locator('[data-admin-view="connect"]').click()
        writes=[]
        page.on("request",lambda request:writes.append(request.url) if request.method=="POST" and request.url.endswith("/admin/agent-credentials") else None)
        page.locator("#create-agent-credential").evaluate("form=>{form.requestSubmit();form.requestSubmit();}")
        page.locator("#agent-credential-dialog").wait_for(state="visible")
        assert len(writes)==1
        username=page.locator("#agent-credential-username").input_value()
        secret=page.locator("#agent-credential-secret").input_value()
        page.locator('[data-field="agent-credential-username"]').click()
        assert page.evaluate("navigator.clipboard.readText()") == username
        page.keyboard.press("Escape")
        playwright.expect(page.locator("#agent-credential-dialog")).not_to_be_visible()
        playwright.expect(page.locator("#agent-credential-secret")).to_have_value("")
        playwright.expect(page.locator("#agent-credential-username")).to_have_value("")
        xml=b"<REQUEST><CONTENT><HARDWARE><UUID>BROWSER-KNOWN-UUID</UUID><NAME>Browser-Known</NAME></HARDWARE><VERSIONCLIENT>1.20</VERSIONCLIENT></CONTENT><DEVICEID>Browser-Known</DEVICEID><QUERY>INVENTORY</QUERY></REQUEST>"
        basic=base64.b64encode(f"{username}:{secret}".encode()).decode()
        assert page.request.post(live_server+"/glpi-agent",headers={"Authorization":f"Basic {basic}","Content-Type":"application/xml"},data=xml).status==200
        claim=page.request.post(live_server+"/agent/re-enrolments",data={"identifier_type":"SMBIOS_UUID","identifier_value":"BROWSER-KNOWN-UUID","computer_name":"Browser-Known","installer_version":"0.1.7"})
        assert claim.status==202
        page.locator('[data-admin-view="recovery"]').click()
        page.locator("#refresh-agent-reenrolments").click()
        row=page.locator("#agent-reenrolments-list .credential-row",has_text="Browser-Known")
        row.wait_for()
        assert "срок до" in row.inner_text()
        row.get_by_role("button",name="Подтвердить",exact=True).click()
        assert "BROWSER-KNOWN-UUID" in page.locator("#confirmation-description").inner_text()
        page.locator("#confirmation-form").evaluate("form=>{form.requestSubmit();form.requestSubmit();}")
        page.locator("#confirmation-dialog").wait_for(state="hidden")
        page.locator("#agent-reenrolments-list .credential-row",has_text="Browser-Known").get_by_text("Подтверждён",exact=True).wait_for()
        page.locator('[data-admin-view="connect"]').click()
        assert page.locator("#agent-credentials-list .credential-row",has_text=username).get_by_text("Отозван",exact=True).is_visible()

        page.evaluate("location.hash='location-access'")
        form=page.locator("#create-user")
        form.locator('[name="username"]').fill("browser-worker")
        form.locator('[name="password"]').fill("test-password")
        form.get_by_role("button",name="Создать пользователя").click()
        page.locator("#users-list").get_by_text("browser-worker",exact=True).wait_for()
        form.locator('[name="username"]').fill("browser-worker")
        form.locator('[name="password"]').fill("test-password")
        form.get_by_role("button",name="Создать пользователя").click()
        form.locator(".form-error").wait_for(state="visible")
        assert form.locator('[name="username"]').input_value()=="browser-worker"
        assert form.locator('[name="password"]').input_value()=="test-password"
        assert form.get_by_role("button",name="Создать пользователя").is_enabled()
        form.locator('[name="username"]').fill("browser-other")
        page.route("**/admin/users",lambda route:route.fulfill(status=503,json={"detail":"Users temporarily unavailable"}) if route.request.method=="GET" else route.continue_())
        form.get_by_role("button",name="Создать пользователя").click()
        page.locator("#access-load-error").wait_for(state="visible")
        assert "список недоступен" in page.locator("#toast").inner_text().lower()
        assert page.locator("#access-user option:checked").inner_text().startswith("browser-worker")
        page.unroute("**/admin/users")
        page.locator("#refresh-access").click()
        page.locator("#users-list").get_by_text("browser-other",exact=True).wait_for()
        other_id=page.locator("#access-user option",has_text="browser-other").get_attribute("value")
        page.locator("#access-user").select_option(other_id)
        assert page.request.patch(live_server+f"/admin/users/{other_id}",headers={"X-AssetGuard-Admin-Token":os.environ["ASSETGUARD_ADMIN_SHARED_SECRET"]},data={"active":False}).status==200
        page.locator("#refresh-access").click()
        page.locator("#users-list .access-row",has_text="browser-other").get_by_text("Вход отключён",exact=True).wait_for()
        assert page.locator("#access-user option:checked").inner_text().startswith("browser-worker")
        for width in (1366,768,390,320):
            page.set_viewport_size({"width":width,"height":900})
            assert page.locator("body").evaluate("element=>element.scrollWidth<=element.clientWidth"),width
            page.evaluate("window.scrollTo(0,0)")
            if width in (1366,390):capture(f"access-{'desktop' if width==1366 else 'mobile'}.png")
        assert not errors,errors
        context.close();browser.close()


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
        assert page.get_by_role("heading", name="Обзор", exact=True).is_visible()
        assert page.get_by_role("heading", name="Что требует внимания").is_visible()
        assert page.locator("#overview .metric-card").count() == 4
        assert page.locator("#overview .overview-focus-grid").is_visible()
        assert page.locator("#setup-guide").is_visible()

        for viewport in ({"width": 1920, "height": 1080}, {"width": 1366, "height": 768}, {"width": 768, "height": 900}, {"width": 390, "height": 900}):
            page.set_viewport_size(viewport)
            assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
            if viewport["width"] == 390:
                page.locator("#toast").evaluate("node => { node.hidden = true; }")
                capture_redesign_preview(page, "overview-mobile.png")
        assert page.locator("#nav-toggle").is_visible()

        # Desktop uses a persistent application sidebar and one visible route.
        page.set_viewport_size({"width": 1280, "height": 900})
        sidebar_width = page.locator(".app-header").evaluate("element => element.getBoundingClientRect().width")
        assert 240 <= sidebar_width <= 280
        assert page.locator("#overview").is_visible()
        assert page.locator("#devices").is_hidden()
        page.locator("#toast").evaluate("node => { node.hidden = true; }")
        capture_redesign_preview(page, "overview-desktop.png")
        page.locator("#main-nav a[href='#incidents']").click()
        page.locator("#incidents").wait_for(state="visible")
        assert page.locator(".page-intro").get_by_role("heading", name="Инциденты", exact=True).is_visible()
        page.go_back()
        page.locator("#overview").wait_for(state="visible")

        assert page.locator("#main-nav > a:visible").count() == 5
        page.locator("#administration-nav").click()
        page.locator("#agent-credentials").wait_for(state="visible")
        assert page.locator("#administration-nav").get_attribute("aria-current") == "page"
        assert page.locator("#agent-fleet-panel").is_visible()
        assert page.locator("#agent-install-panel").is_hidden()
        page.locator("#agent-fleet-list").get_by_text("Компьютеры Agent ещё не подключены", exact=True).wait_for()
        page.locator("#agent-fleet-list").get_by_role("button", name="Подключить компьютер").click()
        assert page.locator("#agent-fleet-panel").is_hidden()
        assert page.locator("#agent-install-panel").is_visible()
        assert page.locator("#agent-keys-panel").is_visible()
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
        page.locator('[data-admin-view="recovery"]').click()
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
        assert page.locator("#show-create").inner_text() == "Добавить имущество"
        assert page.locator("#assets a[href='#data-exchange']").count() == 0
        page.locator("#registry-tools summary").click()
        assert page.locator("#data-exchange-shortcut").is_visible()
        page.locator("#registry-tools summary").click()
        page.locator("#toast").evaluate("node => { node.hidden = true; }")
        capture_redesign_preview(page, "registry-desktop.png")
        page.set_viewport_size({"width": 390, "height": 900})
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        capture_redesign_preview(page, "registry-mobile.png")

        page.set_viewport_size({"width": 900, "height": 900})
        page.locator("#nav-toggle").click()
        assert page.locator("#main-nav a[href='#devices']").is_visible()
        page.locator("#main-nav a[href='#devices']").click()

        page.locator("#show-create").click()
        form = page.locator("#create-asset")
        form.locator('[name="inventory_number"]').fill(inventory_number)
        form.locator('[name="name"]').fill("Browser E2E workstation")
        page.set_viewport_size({"width": 1280, "height": 900})
        capture_redesign_preview(page, "asset-create-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        capture_redesign_preview(page, "asset-create-mobile.png")
        page.set_viewport_size({"width": 900, "height": 900})
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

        page.locator("#registry-tools summary").click()
        page.locator("#data-exchange-shortcut").click()
        page.locator("#data-exchange").wait_for(state="visible")
        assert page.url.endswith("#data-exchange")
        assert page.locator("#devices").is_hidden()
        assert page.locator(".page-intro").get_by_role("heading", name="Импорт и экспорт", exact=True).is_visible()
        page.set_viewport_size({"width": 1280, "height": 900})
        capture_redesign_preview(page, "data-exchange-desktop.png")
        page.set_viewport_size({"width": 390, "height": 900})
        assert page.locator("body").evaluate("element => element.scrollWidth <= element.clientWidth")
        capture_redesign_preview(page, "data-exchange-mobile.png")
        page.set_viewport_size({"width": 900, "height": 900})

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
        page.locator("#data-exchange-status").filter(has_text="Изменения не отправлены").wait_for()
        page.get_by_role("link", name="Вернуться в реестр").click()
        page.locator("#devices").wait_for(state="visible")

        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#locations']").click()
        page.locator("#locations").wait_for(state="visible")
        page.locator("#show-building-create").click()
        page.locator("#building-create-dialog").wait_for(state="visible")
        page.locator("#create-building [name='name']").fill(ui_building_name)
        page.locator("#create-building").get_by_role("button", name="Добавить корпус").click()
        page.locator("#building-create-dialog").wait_for(state="hidden")
        ui_building = page.locator("#location-tree .location-building", has_text=ui_building_name).first
        ui_building.wait_for()
        ui_building.get_by_role("button", name="Добавить этаж").click()
        location_dialog = page.locator("#location-create-dialog")
        location_dialog.wait_for(state="visible")
        assert location_dialog.get_by_role("heading", name="Добавить этаж").is_visible()
        page.locator("#location-create-name").fill(ui_floor_name)
        page.locator("#location-create-submit").click()
        location_dialog.wait_for(state="hidden")
        ui_building.get_by_text(f"Этаж {ui_floor_name}", exact=True).wait_for()
        ui_building.get_by_role("button", name="Добавить кабинет").click()
        location_dialog.wait_for(state="visible")
        page.locator("#location-create-name").fill(ui_room_name)
        page.locator("#location-create-submit").click()
        location_dialog.wait_for(state="hidden")
        ui_building.get_by_text(f"Кабинет {ui_room_name}", exact=False).wait_for()
        assert page.locator("main > .page-section:visible").count() == 1
        page.set_viewport_size({"width": 1280, "height": 900})
        capture_redesign_preview(page, "locations-desktop.png")
        page.set_viewport_size({"width": 900, "height": 900})

        page.locator("#nav-toggle").click()
        page.locator("#main-nav a[href='#devices']").click()
        page.locator("#devices").wait_for(state="visible")
        row = page.locator("#assets tr", has_text=inventory_number)
        row.wait_for()
        open_button = row.locator(".device-open-link")
        assert open_button.is_visible()
        open_button.click()
        assert page.url.endswith(f"#asset={row.get_attribute('data-asset-id')}")
        page.locator("#detail-title").filter(has_text="Browser E2E workstation").wait_for()
        page.set_viewport_size({"width": 1280, "height": 900})
        capture_redesign_preview(page, "asset-detail-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        capture_redesign_preview(page, "asset-detail-mobile.png")
        page.set_viewport_size({"width": 900, "height": 900})
        assert page.get_by_text("Компьютер пока не связан с Agent").is_visible()
        assert page.get_by_role("heading", name="Состав компьютера").is_hidden()
        assert page.get_by_role("tab", name="Оборудование").is_hidden()
        assert page.get_by_role("tab", name="Эталон и изменения").is_hidden()
        assert page.get_by_role("tab", name="Технические данные").is_hidden()
        assert page.get_by_role("tab", name="Сведения").get_attribute("aria-selected") == "true"
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
        capture_redesign_preview(page, "locations-mobile.png")
        room_row = page.locator(".location-room", has_text=f"Кабинет {room_name}")
        room_row.get_by_role("button", name="Открыть кабинет").click()
        page.locator("#room-detail-title").filter(has_text=f"Кабинет {room_name}").wait_for()
        capture_redesign_preview(page, "room-mobile.png")
        page.set_viewport_size({"width": 1280, "height": 900})
        capture_redesign_preview(page, "room-desktop.png")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#room-tabs [role='tab']").count() == 6
        assert page.locator("#room-tab-content").get_by_text("E2E ответственный").is_visible()
        page.locator('[data-room-tab="checks"]').click()
        assert page.locator("#room-tab-content").get_by_role("heading", name="Компьютеры и эталоны").is_visible()
        assert page.locator("#room-tab-content").get_by_role("heading", name="Проверка по фото").is_visible()
        page.locator('[data-room-tab="overview"]').click()
        page.locator("#room-tools summary").click()
        page.locator("#room-edit-action").click()
        page.locator("#room-edit-dialog").wait_for(state="visible")
        page.locator("#room-edit-contact").fill("e2e@example.org")
        page.locator("#room-edit-submit").click()
        page.locator("#room-edit-dialog").wait_for(state="hidden")
        assert page.locator("#room-tab-content").get_by_text("e2e@example.org").is_visible()
        page.locator('[data-room-tab="inventory"]').click()
        assert page.locator("#room-tab-content").get_by_text("Проектор кабинета").is_visible()
        page.locator('[data-room-tab="history"]').click()
        assert page.locator("#room-tab-content").get_by_text("Имущество добавлено").is_visible()
        page.locator("#room-inspection-action").click()
        page.locator("#room-inspection-dialog").wait_for(state="visible")
        page.locator("#room-inspection-items .inspection-result-input").select_option("DAMAGED")
        page.locator("#room-inspection-items .inspection-affected-input").fill("1")
        page.locator("#room-inspection-comment").fill("E2E обход кабинета")
        page.locator("#room-inspection-submit").click()
        page.locator("#inspection-review-step").wait_for(state="visible")
        page.locator("#room-inspection-submit").click()
        page.locator("#room-inspection-dialog").wait_for(state="hidden")
        page.locator("#room-tab-content").get_by_text("E2E обход кабинета").wait_for()
        assert page.locator("#room-tab-content").get_by_text("Повреждено · 1").is_visible()
        page.locator('[data-room-tab="incidents"]').click()
        assert page.locator("#room-tab-content").get_by_text("Проектор кабинета: повреждено").is_visible()
        page.locator("#room-tab-content .physical-incident-action").click()
        page.locator("#physical-incident-action-select").select_option("REPAIR")
        page.locator("#physical-incident-comment").fill("Передать проектор в ремонт")
        page.locator("#physical-incident-submit").click()
        page.locator("#physical-incident-dialog").wait_for(state="hidden")
        page.locator("#room-tab-content").get_by_text("Ремонт").wait_for()
        page.locator("#room-tools summary").click()
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
        capture_redesign_preview(page, "incident-detail-desktop.png")

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
        capture_redesign_preview(page, "incident-decision-mobile.png")
        page.locator("#incident-decision-submit").click()
        dialog.wait_for(state="hidden")
        page.locator("#incident-detail-status").get_by_text("Закрыто").wait_for()
        assert page.locator("#incident-detail-decisions").get_by_text("Плановая замена модуля подтверждена").is_visible()
        page.locator("#incident-device-action").get_by_role("button", name="Карточка имущества").click()
        page.locator("#detail-title").filter(has_text="Incident E2E workstation").wait_for()
        page.locator("[data-asset-tab=technical]").click()
        assert page.locator("#device-system").get_by_text("Версия Agent").is_visible()
        assert page.locator("#device-system").get_by_text("1.20", exact=True).is_visible()
        assert page.locator("#device-system").get_by_text("Версия установщика").is_visible()
        assert page.locator("#device-system").get_by_text("0.1.6", exact=True).is_visible()

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
        assert page.get_by_role("tab", name="Сведения").get_attribute("aria-selected") == "true"
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
        assert page.get_by_role("heading", name="Обзор", exact=True).is_visible()
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
            capture_redesign_preview(page, name)
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
        assert page.locator("#assets .status-pill").get_by_text("Ручной учёт", exact=True).is_visible()

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


def test_import_to_room_inspection_preserves_selection_and_reviews_before_save(live_server):
    playwright = pytest.importorskip("playwright.sync_api")
    headers = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}

    def spreadsheet(rows, filename="school.xlsx"):
        workbook = Workbook()
        workbook.active.append(["inventory_number", "name", "asset_type", "quantity", "unit", "building", "floor", "room"])
        for row in rows:
            workbook.active.append(row)
        stream = BytesIO()
        workbook.save(stream)
        workbook.close()
        return {"name": filename, "mimeType": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "buffer": stream.getvalue()}

    valid = spreadsheet([
        ["DESKS", "Desks", "Furniture", 8, "шт.", "Main", "1", "101"],
        ["PROJECTOR", "Projector", "Projector", 1, "шт.", "Main", "1", "101"],
        ["CHAIRS", "Chairs", "Furniture", 12, "шт.", "Main", "1", "101"],
        ["EXCLUDED", "Excluded equipment", "Other", 1, "шт.", "Main", "1", "102"],
    ])
    invalid = spreadsheet([
        ["DESKS", "Desks", "Furniture", 8],
        ["BAD", "", "Furniture", 1],
        ["BAD-QUANTITY", "Invalid quantity", "Furniture", 1.5],
    ], "invalid.xlsx")
    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page(viewport={"width": 1366, "height": 900})
        page.set_default_timeout(10_000)
        failures = []
        page.on("pageerror", lambda error: failures.append(str(error)))

        def get(path):
            response = page.request.get(live_server + path, headers=headers)
            assert response.ok, response.text()
            return response.json()

        def capture(name):
            if os.environ.get("ASSETGUARD_CAPTURE_UI_PREVIEWS") == "1":
                output = Path(__file__).resolve().parents[3] / "outputs/ui-stage3-preview-2026-10-05"
                output.mkdir(parents=True, exist_ok=True)
                page.screenshot(path=str(output / name))

        def verify_modal(dialog_id, prefix):
            for width in (1366, 768, 320, 390):
                page.set_viewport_size({"width": width, "height": 900})
                assert_no_page_overflow(page, width)
                assert page.locator(dialog_id).evaluate("element => element.scrollWidth <= element.clientWidth"), width
                if width in (1366, 390):
                    if dialog_id == "#import-preview-dialog":
                        page.locator(".import-preview-body").evaluate("element => element.scrollTop = 0")
                    capture(f"{prefix}-{'desktop' if width == 1366 else 'mobile'}.png")
                    if dialog_id == "#import-preview-dialog" and width == 390:
                        page.locator("#import-preview-samples").evaluate("element => element.scrollIntoView()")
                        capture("import-rows-mobile.png")
            page.set_viewport_size({"width": 1366, "height": 900})

        page.goto(live_server + "/#data-exchange")
        page.locator("#login-mode").click()
        page.locator("#token").fill(get_settings().admin_shared_secret)
        page.locator("#login").click()
        page.locator("#status").filter(has_text="Данные актуальны").wait_for()
        page.locator("#import-assets-file").set_input_files(invalid)
        page.locator("#import-file-errors").wait_for(state="visible")
        assert "строка 3" in page.locator("#import-file-errors").inner_text()
        assert "строка 4" in page.locator("#import-file-errors").inner_text()
        assert get("/admin/assets") == []

        page.locator("#import-assets-file").set_input_files(valid)
        page.locator("#import-preview-dialog").wait_for(state="visible")
        assert "Default Organization" in page.locator("#import-preview-scope").inner_text()
        page.locator('[data-import-row="3"]').uncheck()
        page.locator("#import-preview-filter").select_option("create")
        verify_modal("#import-preview-dialog", "import-preview")
        apply_url = "**/admin/assets/import.xlsx?apply=true"
        page.route(apply_url, lambda route: route.fulfill(status=503, json={"detail": "Controlled test outage"}), times=1)
        page.locator("#apply-import-preview").click()
        page.locator("#import-preview-error").wait_for(state="visible")
        assert not page.locator('[data-import-row="3"]').is_checked()
        assert page.locator("#import-preview-rows").inner_text() == "3"
        assert get("/admin/assets") == []
        page.locator("#apply-import-preview").click()
        page.locator("#import-preview-dialog").wait_for(state="hidden")
        page.locator("#import-result").wait_for(state="visible")
        assert "новых — 3, обновлено — 0, исключено — 1" in page.locator("#data-exchange-status").inner_text()
        assets = get("/admin/assets")
        assert len(assets) == 3
        assert next(asset for asset in assets if asset["inventory_number"] == "PROJECTOR")["asset_type"] == "Projector"
        assert all(asset["room_id"] for asset in assets)
        room_id = assets[0]["room_id"]
        assert len({asset["room_id"] for asset in assets}) == 1
        page.locator("#import-assets-file").set_input_files(valid)
        page.locator("#import-preview-dialog").wait_for(state="visible")
        assert page.locator("#import-preview-updates").inner_text() == "3"
        page.locator('[data-import-row="3"]').uncheck()
        page.locator("#apply-import-preview").click()
        page.locator("#import-preview-dialog").wait_for(state="hidden")
        page.locator("#data-exchange-status").filter(has_text="новых — 0, обновлено — 3, исключено — 1").wait_for()
        assert len(get("/admin/assets")) == 3
        page.locator("#import-result a[href='#locations']").click()
        page.locator(f'.room-report[data-room="{room_id}"]').click()
        page.locator("#room-detail-title").filter(has_text="101").wait_for()
        page.locator("#room-tools summary").click()
        page.locator("#room-qr-action").click()
        page.locator("#asset-qr-dialog").wait_for(state="visible")
        assert "Кабинет 101" in page.locator("#asset-qr-title").inner_text()
        page.locator("#asset-qr-dialog").press("Escape")
        projector_asset = next(asset for asset in assets if asset["inventory_number"] == "PROJECTOR")
        page.goto(f"{live_server}/#room-audit={room_id}")
        page.locator("#room-inspection-dialog").wait_for(state="visible")
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.locator("#room-inspection-dialog").evaluate("element => element.scrollWidth <= element.clientWidth")
        assert page.locator("#inspection-code-input").is_visible()
        page.set_viewport_size({"width": 1366, "height": 900})
        page.locator("#inspection-code-input").fill(f"https://assetguard.example/#asset={projector_asset['id']}")
        page.locator("#inspection-code-submit").click()
        projector_draft = page.locator("#room-inspection-items .inspection-item", has=page.get_by_text("Projector", exact=True))
        assert projector_draft.locator(".inspection-result-input").input_value() == "PRESENT"
        page.locator("#room-inspection-comment").fill("Черновик QR-обхода")
        page.reload()
        page.locator("#room-inspection-dialog").wait_for(state="visible")
        assert page.locator("#room-inspection-comment").input_value() == "Черновик QR-обхода"
        assert projector_draft.locator(".inspection-result-input").input_value() == "PRESENT"
        page.locator("#inspection-draft-reset").click()
        page.locator("#room-inspection-cancel").click()
        page.locator("#room-inspection-action").click()
        assert page.locator(".inspection-result-input").evaluate_all("elements => elements.every(element => element.value === '')")
        page.locator("#room-inspection-submit").click()
        assert "3 позиций" in page.locator("#inspection-error").inner_text()

        def inspection_row(name):
            return page.locator("#room-inspection-items .inspection-item", has=page.get_by_text(name, exact=True))

        desks, projector, chairs = (inspection_row(name) for name in ("Desks", "Projector", "Chairs"))
        desks.locator("select").select_option("MISSING")
        desks.locator(".inspection-affected-input").fill("9")
        projector.locator("select").select_option("PRESENT")
        chairs.locator("select").select_option("DAMAGED")
        chairs.locator(".inspection-affected-input").fill("2")
        page.locator("#room-inspection-comment").fill("Controlled school inspection")
        page.locator("#room-inspection-submit").click()
        assert "от 1 до 8" in page.locator("#inspection-error").inner_text()
        desks.locator(".inspection-affected-input").fill("2")
        page.locator("#room-inspection-submit").click()
        page.locator("#inspection-review-step").wait_for(state="visible")
        assert "на месте: 1 · отсутствует: 1 · повреждено: 1" in page.locator("#inspection-review-counts").inner_text()
        assert get(f"/admin/locations/rooms/{room_id}/inspections") == []
        verify_modal("#room-inspection-dialog", "inspection-review")
        inspection_url = f"**/admin/locations/rooms/{room_id}/inspections"
        page.route(inspection_url, lambda route: route.fulfill(status=503, json={"detail": "Controlled test outage"}) if route.request.method == "POST" else route.continue_(), times=1)
        page.locator("#room-inspection-submit").click()
        page.locator("#inspection-error").wait_for(state="visible")
        assert page.locator("#inspection-review-step").is_visible()
        assert get(f"/admin/locations/rooms/{room_id}/inspections") == []
        page.locator("#inspection-review-back").click()
        assert desks.locator(".inspection-affected-input").input_value() == "2"
        chairs.locator(".inspection-affected-input").fill("1")
        page.locator("#room-inspection-submit").click()
        page.locator("#room-inspection-form").evaluate("form => { form.requestSubmit(); form.requestSubmit(); }")
        page.locator("#room-inspection-dialog").wait_for(state="hidden")
        page.locator("#room-tab-content .workflow-receipt").wait_for()
        page.locator("#room-tab-content").get_by_text("Controlled school inspection", exact=True).wait_for()
        inspections = get(f"/admin/locations/rooms/{room_id}/inspections")
        assert len(inspections) == 1
        assert len(inspections[0]["items"]) == 3
        assert sorted(item["affected_quantity"] for item in inspections[0]["items"]) == [0, 1, 2]
        assert len(get("/admin/locations/physical-incidents")) == 2
        capture("inspection-result-desktop.png")
        page.reload()
        page.locator("#room-detail-title").filter(has_text="101").wait_for()
        page.locator('[data-room-tab="inspection"]').click()
        page.locator("#room-tab-content").get_by_text("Controlled school inspection", exact=True).wait_for()
        page.set_viewport_size({"width": 390, "height": 900})
        assert_no_page_overflow(page, 390)
        capture("inspection-result-mobile.png")
        assert failures == [], failures
        browser.close()
