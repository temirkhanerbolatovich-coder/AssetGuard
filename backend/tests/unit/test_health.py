import asyncio

import httpx

from assetguard.app import app


def test_health_reports_service_status() -> None:
    async def request_health() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/health")

    response = asyncio.run(request_health())

    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "service": "assetguard",
        "version": "0.1.0",
    }


def test_readiness_checks_database() -> None:
    async def request_readiness() -> httpx.Response:
        transport = httpx.ASGITransport(app=app)
        async with httpx.AsyncClient(
            transport=transport,
            base_url="http://testserver",
        ) as client:
            return await client.get("/health/ready")

    response = asyncio.run(request_readiness())

    assert response.status_code == 200
    assert response.json() == {"status": "ready", "service": "assetguard"}
