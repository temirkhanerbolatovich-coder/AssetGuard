"""Non-sensitive operational health endpoint."""

from fastapi import APIRouter


router = APIRouter(tags=["operations"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the API process is reachable without exposing dependencies."""
    return {
        "status": "ok",
        "service": "assetguard",
        "version": "0.1.0",
    }

