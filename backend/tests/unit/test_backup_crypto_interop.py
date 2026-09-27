from __future__ import annotations

import importlib.util
import shutil
import subprocess
from pathlib import Path

import pytest


REPOSITORY_ROOT = Path(__file__).parents[3]
WINDOWS_CRYPTO = REPOSITORY_ROOT / "scripts" / "windows" / "backup-crypto.ps1"
LINUX_CRYPTO = REPOSITORY_ROOT / "scripts" / "linux" / "assetguard-backup-crypto.py"


def _load_linux_crypto():
    spec = importlib.util.spec_from_file_location("assetguard_backup_crypto", LINUX_CRYPTO)
    assert spec and spec.loader
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _powershell_literal(path: Path) -> str:
    return str(path).replace("'", "''")


def test_agbk1_is_portable_between_powershell_and_python(tmp_path: Path) -> None:
    pwsh = shutil.which("pwsh")
    if not pwsh:
        pytest.skip("PowerShell 7 is required for the cross-platform backup test.")

    plaintext = tmp_path / "source.sql"
    powershell_backup = tmp_path / "powershell.agbackup"
    python_restore = tmp_path / "python-restore.sql"
    python_backup = tmp_path / "python.agbackup"
    powershell_restore = tmp_path / "powershell-restore.sql"
    passphrase = "assetguard-test-passphrase-123"
    plaintext.write_bytes("SELECT 'AssetGuard переносимый backup';\n".encode())

    protect = (
        f". '{_powershell_literal(WINDOWS_CRYPTO)}'; "
        f"$passphrase=ConvertTo-SecureString '{passphrase}' -AsPlainText -Force; "
        f"Protect-AssetGuardBackup -InputFile '{_powershell_literal(plaintext)}' "
        f"-OutputFile '{_powershell_literal(powershell_backup)}' -Passphrase $passphrase"
    )
    subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", protect], check=True)

    crypto = _load_linux_crypto()
    crypto.decrypt(powershell_backup, python_restore, passphrase)
    assert python_restore.read_bytes() == plaintext.read_bytes()

    crypto.encrypt(plaintext, python_backup, passphrase)
    unprotect = (
        f". '{_powershell_literal(WINDOWS_CRYPTO)}'; "
        f"$passphrase=ConvertTo-SecureString '{passphrase}' -AsPlainText -Force; "
        f"Unprotect-AssetGuardBackup -InputFile '{_powershell_literal(python_backup)}' "
        f"-OutputFile '{_powershell_literal(powershell_restore)}' -Passphrase $passphrase"
    )
    subprocess.run([pwsh, "-NoProfile", "-NonInteractive", "-Command", unprotect], check=True)
    assert powershell_restore.read_bytes() == plaintext.read_bytes()
