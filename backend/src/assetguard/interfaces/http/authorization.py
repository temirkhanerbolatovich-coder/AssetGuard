"""Reusable authentication and role dependencies for HTTP routes."""

from __future__ import annotations

import secrets
from typing import Annotated

from fastapi import Depends, Header, HTTPException, status
from sqlalchemy.orm import Session

from assetguard.infrastructure.config import get_settings
from assetguard.infrastructure.database import get_session
from assetguard.modules.identity.auth import AuthPrincipal, session_principal


def require_admin(
    token: Annotated[str | None, Header(alias="X-AssetGuard-Admin-Token")] = None,
    session: Session = Depends(get_session),
) -> AuthPrincipal:
    settings = get_settings()
    valid_shared_secrets = (
        settings.admin_shared_secret,
        settings.previous_admin_shared_secret,
    )
    if token and any(
        candidate and secrets.compare_digest(token, candidate)
        for candidate in valid_shared_secrets
    ):
        return AuthPrincipal(
            user_id=None,
            username="bootstrap-admin",
            role="ADMIN",
            session_id=None,
            organization_id=None,
        )

    principal = session_principal(session, token) if token else None
    if not principal or principal.role != "ADMIN":
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid administrator credentials.",
        )
    return principal


def require_viewer(
    token: Annotated[str | None, Header(alias="X-AssetGuard-Admin-Token")] = None,
    session: Session = Depends(get_session),
) -> AuthPrincipal:
    settings = get_settings()
    valid_shared_secrets = (
        settings.admin_shared_secret,
        settings.previous_admin_shared_secret,
        settings.viewer_shared_secret,
    )
    if token and any(
        candidate and secrets.compare_digest(token, candidate)
        for candidate in valid_shared_secrets
    ):
        role = (
            "VIEWER"
            if settings.viewer_shared_secret
            and secrets.compare_digest(token, settings.viewer_shared_secret)
            else "ADMIN"
        )
        return AuthPrincipal(
            user_id=None,
            username=f"shared-{role.lower()}",
            role=role,
            session_id=None,
            organization_id=None,
        )

    principal = session_principal(session, token) if token else None
    allowed_roles = {"ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"}
    if not principal or principal.role not in allowed_roles:
        raise HTTPException(
            status.HTTP_401_UNAUTHORIZED,
            "Invalid AssetGuard credentials.",
        )
    return principal
