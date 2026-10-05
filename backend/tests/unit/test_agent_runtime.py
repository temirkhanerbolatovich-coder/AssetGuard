"""Execute the shipped PowerShell queue against disk and controlled HTTP responses."""
import json
import os
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
import shutil
import subprocess
from threading import Thread

import pytest

ROOT = Path(__file__).resolve().parents[3]
RUNTIME = ROOT / "scripts/windows/assetguard-agent-runtime.ps1"
CONTRACT = ROOT / "backend/tests/fixtures/agent-runtime-contract.ps1"


def run_contract(tmp_path, scenario, gateway=None):
    powershell = os.environ.get("ASSETGUARD_AGENT_TEST_POWERSHELL") or shutil.which("pwsh")
    if not powershell:
        pytest.skip("PowerShell 7 is required for the Agent runtime contract.")
    arguments = [powershell, "-NoProfile", "-NonInteractive", "-File", str(CONTRACT),
                 "-Root", str(tmp_path), "-Runtime", str(RUNTIME), "-Scenario", scenario]
    if gateway:
        arguments.extend(["-GatewayUri", gateway])
    result = subprocess.run(arguments, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=60)
    assert result.returncode == 0, result.stderr
    assert json.loads(result.stdout)["passed"]


@pytest.mark.parametrize("scenario", ["offline_fifo", "batch_limit", "lost_ack", "jitter_retry", "queue_recovery_lock", "quota_corruption", "auth_rejected"])
def test_durable_agent_queue(tmp_path, scenario):
    run_contract(tmp_path, scenario)


def test_agent_requires_xml_ack_and_does_not_follow_redirects(tmp_path):
    requests = []
    responses = [(200, b"<html>Proxy error</html>"), (302, b""), (401, b""), (429, b""),
                 (200, b"x" * 65537),
                 (200, b"<REPLY><RESPONSE>SEND</RESPONSE></REPLY>")]

    class Receiver(BaseHTTPRequestHandler):
        def do_POST(self):
            assert self.path == "/glpi-agent"
            body = self.rfile.read(int(self.headers["Content-Length"]))
            requests.append(body)
            status, response = responses[len(requests) - 1]
            self.send_response(status)
            self.send_header("Content-Type", "application/xml")
            if status == 302:
                self.send_header("Location", "/must-not-follow")
            if status == 429:
                self.send_header("Retry-After", "120")
            self.end_headers()
            self.wfile.write(response)

        def log_message(self, *args):
            pass

    server = ThreadingHTTPServer(("127.0.0.1", 0), Receiver)
    thread = Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        run_contract(tmp_path, "http_ack", f"http://127.0.0.1:{server.server_port}/glpi-agent")
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=5)
    assert len(requests) == 6
    assert len(set(requests)) == 1, "Retry must keep the first report immutable."
