#!/usr/bin/env python3
"""Encrypt an AssetGuard SQL backup using the portable AGBK1 AES-256-GCM format."""
from __future__ import annotations

import argparse
import os
from pathlib import Path

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from cryptography.hazmat.primitives.hashes import SHA256
from cryptography.hazmat.primitives.kdf.pbkdf2 import PBKDF2HMAC

MAGIC = b"AGBK1"
ITERATIONS = 210_000


def encrypt(input_path: Path, output_path: Path, passphrase: str) -> None:
    if len(passphrase) < 16:
        raise ValueError("Backup passphrase must contain at least 16 characters.")
    salt, nonce = os.urandom(16), os.urandom(12)
    key = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(passphrase.encode())
    plaintext = input_path.read_bytes()
    encrypted = AESGCM(key).encrypt(nonce, plaintext, MAGIC)
    # cryptography returns ciphertext followed by the 16-byte GCM tag.
    ciphertext, tag = encrypted[:-16], encrypted[-16:]
    output_path.write_bytes(MAGIC + salt + nonce + tag + ciphertext)


def decrypt(input_path: Path, output_path: Path, passphrase: str) -> None:
    if len(passphrase) < 16:
        raise ValueError("Backup passphrase must contain at least 16 characters.")
    payload = input_path.read_bytes()
    if len(payload) < 49 or payload[:5] != MAGIC:
        raise ValueError("The selected file is not an AssetGuard encrypted backup.")
    salt, nonce, tag, ciphertext = payload[5:21], payload[21:33], payload[33:49], payload[49:]
    key = PBKDF2HMAC(algorithm=SHA256(), length=32, salt=salt, iterations=ITERATIONS).derive(passphrase.encode())
    output_path.write_bytes(AESGCM(key).decrypt(nonce, ciphertext + tag, MAGIC))


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("operation", choices=("encrypt", "decrypt"))
    parser.add_argument("--input", required=True, type=Path)
    parser.add_argument("--output", required=True, type=Path)
    passphrase_source = parser.add_mutually_exclusive_group(required=True)
    passphrase_source.add_argument("--passphrase")
    passphrase_source.add_argument("--passphrase-stdin", action="store_true")
    args = parser.parse_args()
    passphrase = args.passphrase if args.passphrase is not None else input()
    {"encrypt": encrypt, "decrypt": decrypt}[args.operation](args.input, args.output, passphrase)


if __name__ == "__main__":
    main()
