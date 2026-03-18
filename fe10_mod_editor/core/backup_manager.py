"""Backup file management with MD5 hash verification.

Backup safety rules:
1. Backups contain only original unmodified files
2. MD5 hashes are computed once on first backup, stored in project file
3. Write-once: never overwrite a verified backup
4. Verify before every build: abort on hash mismatch
"""

import hashlib
import os
import shutil
from dataclasses import dataclass

BACKUP_FILES = [
    "FE10Data.cms",
    "shopitem_n.bin",
    "shopitem_m.bin",
    "shopitem_h.bin",
    "fst.bin",
]


@dataclass
class VerifyResult:
    ok: bool
    error: str = ""


def compute_file_hash(filepath: str) -> str:
    """Compute MD5 hash of a file. Returns hex digest string."""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def compute_backup_hashes(backup_dir: str) -> dict[str, str]:
    """Compute MD5 hashes for all expected backup files."""
    hashes = {}
    for fname in BACKUP_FILES:
        path = os.path.join(backup_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing backup file: {fname}")
        hashes[fname] = compute_file_hash(path)
    return hashes


def verify_backup_hashes(backup_dir: str, stored_hashes: dict[str, str]) -> VerifyResult:
    """Verify backup files against stored MD5 hashes."""
    for fname, expected_hash in stored_hashes.items():
        path = os.path.join(backup_dir, fname)
        if not os.path.exists(path):
            return VerifyResult(ok=False, error=f"Missing file: {fname}")
        actual_hash = compute_file_hash(path)
        if actual_hash != expected_hash:
            return VerifyResult(
                ok=False,
                error=f"Hash mismatch for {fname}: expected {expected_hash}, got {actual_hash}",
            )
    return VerifyResult(ok=True)


def restore_backup(backup_dir: str, game_dir: str, shop_dir: str, fst_path: str) -> list[str]:
    """Copy all backup files back to their game directory locations."""
    restored = []
    targets = {
        "FE10Data.cms": os.path.join(game_dir, "FE10Data.cms"),
        "shopitem_n.bin": os.path.join(shop_dir, "shopitem_n.bin"),
        "shopitem_m.bin": os.path.join(shop_dir, "shopitem_m.bin"),
        "shopitem_h.bin": os.path.join(shop_dir, "shopitem_h.bin"),
        "fst.bin": fst_path,
    }
    for fname, target_path in targets.items():
        src = os.path.join(backup_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, target_path)
            restored.append(target_path)
    return restored
