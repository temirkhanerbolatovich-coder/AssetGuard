"""Run the real local Vision baseline-to-warning flow from inside the API container."""
from __future__ import annotations

import json
import os
import time
import urllib.request
import uuid
from pathlib import Path

BASE = "http://127.0.0.1:8000"
HEADERS = {"X-AssetGuard-Admin-Token": os.environ["ASSETGUARD_ADMIN_SHARED_SECRET"]}


def request(path: str, method: str = "GET", payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode()
    headers = {**HEADERS, **({"Content-Type": "application/json"} if data else {})}
    with urllib.request.urlopen(urllib.request.Request(BASE + path, data=data, headers=headers, method=method), timeout=900) as response:
        return json.loads(response.read())


def scan(image: Path, room_id: str) -> dict:
    boundary = "assetguard-" + uuid.uuid4().hex
    body = b"".join((
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"location_room_id\"\r\n\r\n{room_id}\r\n".encode(),
        f"--{boundary}\r\nContent-Disposition: form-data; name=\"image\"; filename=\"{image.name}\"\r\nContent-Type: image/png\r\n\r\n".encode(),
        image.read_bytes(), f"\r\n--{boundary}--\r\n".encode(),
    ))
    headers = {**HEADERS, "Content-Type": f"multipart/form-data; boundary={boundary}"}
    with urllib.request.urlopen(urllib.request.Request(BASE + "/admin/vision/scans", data=body, headers=headers, method="POST"), timeout=900) as response:
        return json.loads(response.read())


suffix = str(int(time.time()))
building = request("/admin/locations/buildings", "POST", {"name": f"Vision demo {suffix}"})
floor = request(f"/admin/locations/buildings/{building['id']}/floors", "POST", {"name": "1"})
room = request(f"/admin/locations/floors/{floor['id']}/rooms", "POST", {"name": "305", "purpose": "Local Vision test"})
first = scan(Path("/tmp/vision-baseline.png"), room["id"])
if first["status"] != "NOT_CHECKED": raise RuntimeError(f"unexpected baseline status: {first['status']}")
baseline = request(f"/admin/vision/rooms/{first['room_id']}/baseline", "POST", {"scan_id": first["id"]})
second = scan(Path("/tmp/vision-warning.png"), room["id"])
if second["status"] != "WARNING" or not second.get("comparison", {}).get("differences"):
    raise RuntimeError(f"expected explainable WARNING, got {second['status']} {second.get('counts')}")
print(json.dumps({"result": "PASS", "baseline_counts": baseline["counts"], "comparison_counts": second["counts"], "differences": second["comparison"]["differences"], "annotated_image_url": second["annotated_image_url"]}))
