from assetguard.interfaces.http.admin_assets import _ram_capacity_bytes


def test_ram_capacity_accepts_glpi_mebibytes_and_bytes() -> None:
    assert _ram_capacity_bytes(8192) == 8 * 1024**3
    assert _ram_capacity_bytes(8 * 1024**3) == 8 * 1024**3
    assert _ram_capacity_bytes(None) is None
