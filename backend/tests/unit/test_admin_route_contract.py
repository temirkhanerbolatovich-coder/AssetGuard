"""Executable role matrix for every protected administrator operation."""

from collections.abc import Iterable
from pathlib import Path
from typing import Literal

import pytest
from fastapi import HTTPException
from fastapi.routing import APIRoute

from assetguard.app import app
from assetguard.interfaces.http import authorization
from assetguard.interfaces.http.admin_assets import router as admin_assets_router
from assetguard.interfaces.http.admin_inventories import router as admin_inventories_router
from assetguard.interfaces.http.admin_locations import router as admin_locations_router
from assetguard.interfaces.http.admin_workflows import router as admin_workflows_router
from assetguard.interfaces.http.authorization import require_admin, require_viewer
from assetguard.interfaces.http.auth import router as auth_router
from assetguard.interfaces.http.health import router as health_router
from assetguard.interfaces.http.vision import router as vision_router
from assetguard.modules.identity.auth import AuthPrincipal

Operation = tuple[str, str]
AccessLevel = Literal["admin", "viewer"]

ADMIN_OPERATIONS: frozenset[Operation] = frozenset(
    {
        ("POST", "/admin/assets/import.xlsx"),
        ("POST", "/admin/assets/import.pdf"),
        ("POST", "/admin/maintenance/evaluate-endpoints"),
        ("POST", "/admin/endpoints/{endpoint_id}/asset/{asset_id}"),
        ("GET", "/admin/locations/organizations"),
        ("POST", "/admin/locations/buildings"),
        ("POST", "/admin/locations/buildings/{building_id}/floors"),
        ("POST", "/admin/locations/floors/{floor_id}/rooms"),
        ("PATCH", "/admin/locations/rooms/{room_id}"),
        ("GET", "/admin/locations/access"),
        ("POST", "/admin/locations/access"),
        ("DELETE", "/admin/locations/access/{access_id}"),
        ("POST", "/admin/snapshots/{snapshot_id}/baseline"),
        ("POST", "/admin/incidents/{incident_id}/decision"),
        ("POST", "/admin/incidents/{incident_id}/resolve"),
        ("GET", "/admin/users"),
        ("POST", "/admin/users"),
        ("PATCH", "/admin/users/{user_id}"),
        ("GET", "/admin/sessions"),
        ("DELETE", "/admin/sessions/{session_id}"),
        ("GET", "/admin/agent-credentials"),
        ("POST", "/admin/agent-credentials"),
        ("POST", "/admin/agent-credentials/{credential_id}/revoke"),
        ("GET", "/admin/agent-re-enrolments"),
        ("POST", "/admin/agent-re-enrolments/{request_id}/approve"),
        ("POST", "/admin/agent-re-enrolments/{request_id}/reject"),
        ("POST", "/admin/vision/scans"),
        ("POST", "/admin/vision/rooms/{room_id}/baseline"),
    }
)

VIEWER_OPERATIONS: frozenset[Operation] = frozenset(
    {
        ("GET", "/admin/operations/status"),
        ("GET", "/admin/assets"),
        ("GET", "/admin/assets/export.xlsx"),
        ("GET", "/admin/assets/export.pdf"),
        ("GET", "/admin/assets/{asset_id}/qr.svg"),
        ("POST", "/admin/assets"),
        ("PATCH", "/admin/assets/{asset_id}"),
        ("GET", "/admin/endpoints"),
        ("GET", "/admin/endpoints/{endpoint_id}"),
        ("GET", "/admin/assets/{asset_id}"),
        ("GET", "/admin/locations/tree"),
        ("GET", "/admin/locations/rooms/{room_id}/report"),
        ("GET", "/admin/locations/rooms/{room_id}/inspections"),
        ("POST", "/admin/locations/rooms/{room_id}/inspections"),
        ("POST", "/admin/locations/physical-incidents/{incident_id}/decision"),
        ("GET", "/admin/locations/physical-incidents/{incident_id}/act.pdf"),
        ("GET", "/admin/locations/rooms/{room_id}/workspace"),
        ("GET", "/admin/endpoints/{endpoint_id}/snapshots"),
        ("GET", "/admin/snapshots/{snapshot_id}"),
        ("GET", "/admin/endpoints/{endpoint_id}/baseline"),
        ("GET", "/admin/changes"),
        ("GET", "/admin/changes/{change_id}"),
        ("GET", "/admin/incidents"),
        ("GET", "/admin/incidents/{incident_id}"),
        ("GET", "/admin/endpoints/{endpoint_id}/history"),
        ("GET", "/admin/inventories"),
        ("GET", "/admin/inventories/{inventory_id}"),
        ("GET", "/admin/vision/rooms"),
        ("GET", "/admin/vision/rooms/{room_id}/scans"),
        ("GET", "/admin/vision/scans/{scan_id}"),
        ("GET", "/admin/vision/scans/{scan_id}/image"),
        ("GET", "/admin/vision/rooms/{room_id}/baseline"),
    }
)

ALLOWED_ROLES: dict[AccessLevel, frozenset[str]] = {
    "admin": frozenset({"ADMIN"}),
    "viewer": frozenset(
        {"ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"}
    ),
}

ADMIN_ROUTERS = (
    health_router,
    admin_assets_router,
    admin_locations_router,
    admin_workflows_router,
    admin_inventories_router,
    auth_router,
    vision_router,
)


def _dependency_calls(dependant: object) -> Iterable[object]:
    yield dependant.call
    for dependency in dependant.dependencies:
        yield from _dependency_calls(dependency)


def _admin_routes() -> dict[Operation, APIRoute]:
    operations: dict[Operation, APIRoute] = {}
    for router in ADMIN_ROUTERS:
        for route in router.routes:
            if not isinstance(route, APIRoute) or not route.path.startswith("/admin/"):
                continue
            for method in route.methods - {"HEAD", "OPTIONS"}:
                operations[(method, route.path)] = route
    return operations


def _openapi_admin_operations() -> set[Operation]:
    operations: set[Operation] = set()
    for path, path_item in app.openapi()["paths"].items():
        if not path.startswith("/admin/"):
            continue
        for method in path_item:
            if method.upper() in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
                operations.add((method.upper(), path))
    return operations


def test_every_admin_operation_has_an_explicit_access_level() -> None:
    expected_operations = ADMIN_OPERATIONS | VIEWER_OPERATIONS
    assert ADMIN_OPERATIONS.isdisjoint(VIEWER_OPERATIONS)
    assert _admin_routes().keys() == expected_operations
    assert _openapi_admin_operations() == expected_operations


@pytest.mark.parametrize(
    ("access_level", "operations"),
    (("admin", ADMIN_OPERATIONS), ("viewer", VIEWER_OPERATIONS)),
)
def test_every_admin_operation_uses_its_declared_auth_dependency(
    access_level: AccessLevel,
    operations: frozenset[Operation],
) -> None:
    routes = _admin_routes()
    for operation in operations:
        dependency_calls = set(_dependency_calls(routes[operation].dependant))
        assert require_viewer in dependency_calls or require_admin in dependency_calls
        if access_level == "admin":
            assert require_admin in dependency_calls, operation
        else:
            assert require_admin not in dependency_calls, operation
            assert require_viewer in dependency_calls, operation


@pytest.mark.parametrize("access_level", ("admin", "viewer"))
@pytest.mark.parametrize(
    "role",
    ("ADMIN", "VIEWER", "LOCATION_MANAGER", "INVENTORY_CLERK"),
)
def test_role_dependency_allow_deny_matrix(
    monkeypatch: pytest.MonkeyPatch,
    access_level: AccessLevel,
    role: str,
) -> None:
    principal = AuthPrincipal(
        user_id=None,
        username=f"matrix-{role.lower()}",
        role=role,
        session_id=None,
        organization_id=None,
    )
    monkeypatch.setattr(
        authorization,
        "session_principal",
        lambda _session, _token: principal,
    )
    dependency = require_admin if access_level == "admin" else require_viewer

    if role in ALLOWED_ROLES[access_level]:
        assert dependency(token="matrix-session", session=object()) == principal
    else:
        with pytest.raises(HTTPException) as error:
            dependency(token="matrix-session", session=object())
        assert error.value.status_code == 401


@pytest.mark.parametrize("dependency", (require_admin, require_viewer))
def test_admin_dependencies_reject_anonymous_requests(dependency: object) -> None:
    with pytest.raises(HTTPException) as error:
        dependency(token=None, session=object())
    assert error.value.status_code == 401


def test_access_matrix_documentation_tracks_the_executable_policy() -> None:
    matrix = (
        Path(__file__).parents[3]
        / "docs"
        / "security"
        / "admin-route-access-matrix.md"
    ).read_text(encoding="utf-8")
    assert "60 protected operations" in matrix
    for role in ALLOWED_ROLES["viewer"]:
        assert f"`{role}`" in matrix
