from pathlib import Path

from assetguard.app import app


def test_admin_route_inventory_requires_matrix_maintenance() -> None:
    """Route-count changes must trigger an explicit review of the A/V/E/F matrix."""
    matrix = (Path(__file__).parents[3] / "docs" / "security" / "admin-route-access-matrix.md").read_text(encoding="utf-8")
    admin_paths = {path for path in app.openapi()["paths"] if path.startswith("/admin/")}
    assert len(admin_paths) == 50, "A /admin route changed: update the A/V/E/F access matrix and its tests."
    for heading in ("## Реестр и технические события", "## Помещения, обходы и Vision", "## Управление доступом и устройствами"):
        assert heading in matrix
