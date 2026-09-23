from __future__ import annotations

import asyncio

import httpx

from assetguard.app import app
from assetguard.infrastructure.config import get_settings


def test_named_session_can_be_revoked_and_user_can_be_disabled() -> None:
    asyncio.run(_exercise_auth_lifecycle())


async def _exercise_auth_lifecycle() -> None:
    bootstrap = {"X-AssetGuard-Admin-Token": get_settings().admin_shared_secret}
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        created = await client.post("/admin/users", headers=bootstrap, json={
            "username": "session-admin", "password": "fixture-password-456", "role": "ADMIN",
        })
        assert created.status_code == 201, created.text
        user_id = created.json()["id"]

        login = await client.post("/auth/login", json={
            "username": "session-admin", "password": "fixture-password-456",
        })
        assert login.status_code == 200
        token = login.json()["access_token"]
        named = {"X-AssetGuard-Admin-Token": token}
        assert (await client.get("/admin/assets", headers=named)).status_code == 200

        sessions = await client.get("/admin/sessions", headers=named)
        own_session = next(item for item in sessions.json() if item["username"] == "session-admin")
        assert (await client.delete(f"/admin/sessions/{own_session['id']}", headers=named)).status_code == 204
        assert (await client.get("/admin/assets", headers=named)).status_code == 401

        login_again = await client.post("/auth/login", json={
            "username": "session-admin", "password": "fixture-password-456",
        })
        second_token = login_again.json()["access_token"]
        second_named = {"X-AssetGuard-Admin-Token": second_token}
        assert (await client.post("/auth/logout", headers=second_named)).status_code == 204
        assert (await client.get("/admin/assets", headers=second_named)).status_code == 401

        disabled = await client.patch(f"/admin/users/{user_id}", headers=bootstrap, json={"active": False})
        assert disabled.status_code == 200
        assert (await client.post("/auth/login", json={
            "username": "session-admin", "password": "fixture-password-456",
        })).status_code == 401

