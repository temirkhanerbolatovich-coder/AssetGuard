from assetguard.modules.inventory.raw_inventory import payload_sha256


def test_payload_hash_is_stable_for_equivalent_json_objects() -> None:
    left = {"content": {"memories": []}, "action": "inventory"}
    right = {"action": "inventory", "content": {"memories": []}}

    assert payload_sha256(left) == payload_sha256(right)


def test_payload_hash_changes_when_payload_changes() -> None:
    original = {"content": {"memories": []}}
    changed = {"content": {"memories": [{"serialnumber": "different"}]}}

    assert payload_sha256(original) != payload_sha256(changed)

