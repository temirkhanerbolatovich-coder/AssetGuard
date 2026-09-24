"""Non-sensitive operational health endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends
from fastapi.responses import JSONResponse
from sqlalchemy import text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.orm import Session

from assetguard.infrastructure.database import get_session


router = APIRouter(tags=["operations"])


@router.get("/health")
async def health() -> dict[str, str]:
    """Report that the API process is reachable without exposing dependencies."""
    return {
        "status": "ok",
        "service": "assetguard",
        "version": "0.1.0",
    }


@router.get("/health/ready")
def readiness(session: Annotated[Session, Depends(get_session)]):
    """Return 503 when the API cannot reach its mandatory PostgreSQL database."""
    try:
        session.execute(text("SELECT 1"))
    except SQLAlchemyError:
        # Do not expose database topology or driver messages to an unauthenticated probe.
        return JSONResponse(status_code=503, content={"status": "not_ready", "service": "assetguard"})
    return {"status": "ready", "service": "assetguard"}
