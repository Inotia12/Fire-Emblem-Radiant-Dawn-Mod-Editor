import os
import pytest
from fe10_mod_editor.core.backup_manager import (
    compute_file_hash,
    verify_backup_hashes,
    compute_backup_hashes,
    BACKUP_FILES,
)


def test_compute_file_hash_deterministic(tmp_path):
    path = tmp_path / "test.bin"
    path.write_bytes(b"hello world")
    h1 = compute_file_hash(str(path))
    h2 = compute_file_hash(str(path))
    assert h1 == h2
    assert len(h1) == 32


def test_compute_file_hash_different_content(tmp_path):
    p1 = tmp_path / "a.bin"
    p2 = tmp_path / "b.bin"
    p1.write_bytes(b"hello")
    p2.write_bytes(b"world")
    assert compute_file_hash(str(p1)) != compute_file_hash(str(p2))


def test_verify_backup_hashes_pass(tmp_path):
    p = tmp_path / "test.bin"
    p.write_bytes(b"data")
    h = compute_file_hash(str(p))
    result = verify_backup_hashes(str(tmp_path), {"test.bin": h})
    assert result.ok is True


def test_verify_backup_hashes_fail_mismatch(tmp_path):
    p = tmp_path / "test.bin"
    p.write_bytes(b"data")
    result = verify_backup_hashes(str(tmp_path), {"test.bin": "0000000000000000"})
    assert result.ok is False
    assert "mismatch" in result.error.lower()


def test_verify_backup_hashes_fail_missing(tmp_path):
    result = verify_backup_hashes(str(tmp_path), {"missing.bin": "abc123"})
    assert result.ok is False


def test_compute_backup_hashes_real_files(backup_dir):
    hashes = compute_backup_hashes(backup_dir)
    for fname in BACKUP_FILES:
        assert fname in hashes
        assert len(hashes[fname]) == 32
