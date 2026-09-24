"""HTTP application entry point for AssetGuard."""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from pathlib import Path

from assetguard.interfaces.http.health import router as health_router
from assetguard.interfaces.http.inventories import router as inventories_router
from assetguard.interfaces.http.admin_assets import router as admin_assets_router
from assetguard.interfaces.http.admin_workflows import router as admin_workflows_router
from assetguard.interfaces.http.admin_inventories import router as admin_inventories_router
from assetguard.interfaces.http.auth import router as auth_router
from assetguard.interfaces.http.vision import router as vision_router
from assetguard.interfaces.http.glpi_agent import router as glpi_agent_router
from assetguard.interfaces.http.admin_locations import router as admin_locations_router
from assetguard.infrastructure.http_middleware import SecurityAndRateLimitMiddleware


app = FastAPI(
    title="AssetGuard API",
    version="0.1.0",
    docs_url="/docs",
    redoc_url=None,
)
app.add_middleware(SecurityAndRateLimitMiddleware)
app.include_router(health_router)
app.include_router(inventories_router)
app.include_router(admin_assets_router)
app.include_router(admin_locations_router)
app.include_router(admin_workflows_router)
app.include_router(admin_inventories_router)
app.include_router(auth_router)
app.include_router(vision_router)
app.include_router(glpi_agent_router)
# The frontend is copied next to the backend in the production container
# (``/app/frontend``).  Deriving it from the installed Python package points to
# ``/usr/local/lib/frontend`` after ``pip install`` and breaks a Docker deploy.
FRONTEND_DIRECTORY = Path("/app/frontend")
if not FRONTEND_DIRECTORY.is_dir():
    FRONTEND_DIRECTORY = Path(__file__).resolve().parents[3] / "frontend"

app.mount("/", StaticFiles(directory=FRONTEND_DIRECTORY, html=True), name="frontend")
