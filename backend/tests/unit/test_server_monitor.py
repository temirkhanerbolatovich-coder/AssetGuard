"""Execute the real monitor with local command doubles; no network or host jobs."""

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import time

import pytest


def test_monitor_stale_alert_delivery_dedup_recovery_and_retry(tmp_path):
    git_bash = Path("C:/Program Files/Git/bin/bash.exe")
    bash = str(git_bash) if os.name == "nt" and git_bash.exists() else shutil.which("bash")
    if not bash:
        pytest.skip("Bash is required to execute the Linux monitor contract.")
    commands = tmp_path / "commands"
    commands.mkdir()
    project = tmp_path / "project"
    project.mkdir()
    (project / ".env").write_text("ASSETGUARD_PUBLIC_HOST=monitor.invalid\nASSETGUARD_ADMIN_SHARED_SECRET=monitor-test-admin\n", encoding="utf-8")
    backup = tmp_path / "backup.env"
    backup.write_text(f"ASSETGUARD_BACKUP_SUCCESS_UNIX={int(time.time())}\n", encoding="ascii")
    config = tmp_path / "monitor.env"
    config.write_text(f"ASSETGUARD_TELEGRAM_BOT_TOKEN=monitor-test-token\nASSETGUARD_TELEGRAM_CHAT_ID=monitor-test-chat\nASSETGUARD_BACKUP_STATUS_FILE={backup.as_posix()}\n", encoding="utf-8")
    scripts = {
        "docker": "printf 'postgres\\napi\\ncaddy\\n'",
        "systemctl": "exit 1",
        "df": "printf 'Filesystem Blocks Used Available Capacity Mounted\\nfake 100 10 90 10%% /\\n'",
        "python3": 'exec "$MONITOR_TEST_PYTHON" -S "$@"',
        "curl": '''
case "$*" in
  *api.telegram.org*)
    printf '%s\\n' "$*" >> "$MONITOR_TEST_SENDS"
    cat "$MONITOR_TEST_RESPONSE"
    ;;
  */admin/operations/status*) cat "$MONITOR_TEST_METRICS" ;;
  */health/ready*) printf '{"status":"ready"}' ;;
  *) exit 99 ;;
esac
''',
    }
    if os.name == "nt":
        # NTFS permission management differs from the Linux production host.
        scripts["install"] = 'mkdir -p "${@: -1}"'
    for name, body in scripts.items():
        path = commands / name
        path.write_text("#!/usr/bin/env bash\n" + body + "\n", encoding="utf-8", newline="\n")
        path.chmod(0o755)
    metrics = tmp_path / "metrics.json"
    response = tmp_path / "response.json"
    sends = tmp_path / "sends.txt"
    state = tmp_path / "state"
    env = {
        **os.environ,
        "MONITOR_TEST_PYTHON": sys.executable, "MONITOR_TEST_METRICS": metrics.as_posix(),
        "MONITOR_TEST_SENDS": sends.as_posix(), "MONITOR_TEST_RESPONSE": response.as_posix(),
    }
    monitor = Path(__file__).resolve().parents[3] / "scripts/linux/assetguard-server-monitor.sh"

    def run():
        # Git Bash translates Windows PATH on startup. Set its POSIX PATH inside
        # the shell and fail before execution unless curl resolves to our double.
        wrapper = 'export PATH="$PWD/commands:$PATH"; [[ "$(command -v curl)" == "$PWD/commands/curl" ]] || exit 95; exec bash "$@"'
        return subprocess.run([bash, "--noprofile", "--norc", "-c", wrapper, "monitor-test", str(monitor), "--project-dir", str(project), "--config", str(config), "--state-dir", str(state)],
            cwd=tmp_path, env=env, capture_output=True, text=True, encoding="utf-8", timeout=20)

    def set_metrics(stale):
        metrics.write_text(json.dumps({"agents": {"stale": stale}, "ingest": {"failed": 0}}), encoding="ascii")

    set_metrics(1)
    response.write_text('{"ok":true,"result":{"message_id":123}}', encoding="ascii")
    first = run()
    assert first.returncode == 0, first.stderr
    assert "Agent без свежих данных или offline: 1" in sends.read_text(encoding="utf-8")
    assert "suppressed" in run().stdout
    assert sends.read_text(encoding="utf-8").count("-X POST") == 1
    set_metrics(0)
    healthy = run()
    assert healthy.returncode == 0, healthy.stderr
    assert not (state / "state").exists()
    set_metrics(1)
    assert run().returncode == 0
    assert sends.read_text(encoding="utf-8").count("-X POST") == 2
    set_metrics(0)
    assert run().returncode == 0
    set_metrics(1)
    response.write_text('{"ok":false,"description":"test refusal"}', encoding="ascii")
    refused = run()
    assert refused.returncode != 0
    assert not (state / "state").exists()
    response.write_text('{"ok":true,"result":{"message_id":124}}', encoding="ascii")
    assert run().returncode == 0
    assert (state / "state").exists()
    set_metrics(0)
    assert run().returncode == 0
    metrics.write_text("invalid json", encoding="ascii")
    assert run().returncode == 0
    assert "Операционные данные API некорректны" in sends.read_text(encoding="utf-8")
    set_metrics(0)
    assert run().returncode == 0
    metrics.write_text(json.dumps({"agents": {}, "ingest": {}, "notifications": {"retrying": 2}}), encoding="ascii")
    assert run().returncode == 0
    assert "Уведомления об инцидентах ожидают повтора: 2" in sends.read_text(encoding="utf-8")
    assert "suppressed" in run().stdout
