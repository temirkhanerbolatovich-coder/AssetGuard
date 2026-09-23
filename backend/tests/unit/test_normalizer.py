from assetguard.modules.snapshots.normalizer import normalize_identifier


def test_normalizer_canonicalizes_valid_identifier() -> None:
    assert normalize_identifier("  serial-abc  ") == "SERIAL-ABC"


def test_normalizer_rejects_placeholder_identifier() -> None:
    assert normalize_identifier("To Be Filled By O.E.M.") is None
    assert normalize_identifier("00000000") is None
