import os
import pytest
from fe10_mod_editor.core.lz10 import decompress_lz10, compress_lz10


def test_decompress_lz10_header_check():
    """LZ10 data must start with 0x10 signature byte."""
    with pytest.raises(ValueError, match="Not LZ10"):
        decompress_lz10(b"\x00\x00\x00\x00")


def test_decompress_lz10_literal_only():
    """Decompress a hand-crafted LZ10 payload with only literal bytes."""
    # Header: 0x10, size=3 (LE 24-bit: 03 00 00)
    # Flag byte: 0x00 (8 literal entries)
    # 3 literal bytes: 0x41 0x42 0x43 ("ABC")
    data = bytes([0x10, 0x03, 0x00, 0x00, 0x00, 0x41, 0x42, 0x43])
    result = decompress_lz10(data)
    assert result == b"ABC"


def test_roundtrip_small():
    """Compress then decompress should return original data."""
    original = b"AAAAAABBBBBBCCCCCC" * 10
    compressed = compress_lz10(original)
    decompressed = decompress_lz10(compressed)
    assert decompressed == original


def test_roundtrip_with_real_fe10data(backup_dir):
    """Roundtrip the actual FE10Data.cms backup file."""
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()

    decompressed = decompress_lz10(compressed)
    # Verify decompressed data has the ItemData marker at 0xDF44
    assert len(decompressed) > 0xDF48

    recompressed = compress_lz10(decompressed)
    re_decompressed = decompress_lz10(recompressed)
    assert re_decompressed == decompressed
