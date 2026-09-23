from __future__ import annotations

import os
from uuid import uuid4

import pytest


pytestmark = pytest.mark.skipif(
    os.environ.get("ASSETGUARD_RUN_BROWSER_E2E") != "1",
    reason="Set ASSETGUARD_RUN_BROWSER_E2E=1 to run browser tests.",
)


def test_admin_can_open_dashboard_and_create_asset():
    playwright = pytest.importorskip("playwright.sync_api")
    base_url = os.environ.get("ASSETGUARD_E2E_BASE_URL", "http://127.0.0.1:8000")
    admin_secret = os.environ["ASSETGUARD_ADMIN_SHARED_SECRET"]
    inventory_number = f"E2E-{uuid4().hex[:10]}"

    with playwright.sync_playwright() as runtime:
        browser = runtime.chromium.launch()
        page = browser.new_page()
        page.goto(base_url)
        page.locator("#token").fill(admin_secret)
        page.get_by_role("button", name="Войти").click()
        page.locator("#status").filter(has_text="Данные обновлены").wait_for()

        page.get_by_role("button", name="Добавить актив").click()
        form = page.locator("#create-asset")
        form.locator('[name="inventory_number"]').fill(inventory_number)
        form.locator('[name="name"]').fill("Browser E2E workstation")
        form.locator('[name="room"]').fill("CI room")
        form.get_by_role("button", name="Создать").click()

        row = page.locator("#assets tr", has_text=inventory_number)
        row.wait_for()
        row.click()
        page.locator("#detail-title").filter(has_text=inventory_number).wait_for()
        browser.close()
