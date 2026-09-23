import json
from pathlib import Path


FIXTURE_PATH = Path(__file__).parents[1] / "fixtures" / "glpi-agent-minimal-sanitized.json"
FORBIDDEN_FIELDS = {
    "accesslog",
    "envs",
    "licenseinfos",
    "local_groups",
    "local_users",
    "processes",
    "softwares",
    "users",
}


def test_minimal_glpi_fixture_has_no_forbidden_top_level_categories() -> None:
    payload = json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))
    content_fields = {field.lower() for field in payload["content"]}

    assert content_fields.isdisjoint(FORBIDDEN_FIELDS)
    assert {"hardware", "memories", "storages"}.issubset(content_fields)
