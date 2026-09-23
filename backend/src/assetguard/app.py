"""HTTP application entry point for AssetGuard."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from assetguard.interfaces.http.health import router as health_router
from assetguard.interfaces.http.inventories import router as inventories_router
from assetguard.interfaces.http.admin_assets import router as admin_assets_router
from assetguard.interfaces.http.admin_workflows import router as admin_workflows_router


app = FastAPI(
    title="AssetGuard API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)
app.include_router(health_router)
app.include_router(inventories_router)
app.include_router(admin_assets_router)
app.include_router(admin_workflows_router)
app.mount("/", StaticFiles(directory=Path(__file__).resolve().parents[3] / "frontend", html=True), name="frontend")
