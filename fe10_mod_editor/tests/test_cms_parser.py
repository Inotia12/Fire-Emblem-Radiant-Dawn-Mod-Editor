import struct
import pytest
from fe10_mod_editor.core.cms_parser import resolve_string, parse_cms_header


def test_resolve_string_null_pointer():
    """Pointer value 0 returns None."""
    data = b"\x00" * 100
    assert resolve_string(data, 0) is None


def test_resolve_string_valid():
    """Resolve a pointer to an ASCII string in the data region."""
    # Place "HELLO\0" at file offset 0x30
    # Stored pointer = 0x30 - 0x20 = 0x10
    data = bytearray(0x40)
    data[0x30:0x36] = b"HELLO\x00"
    assert resolve_string(bytes(data), 0x10) == "HELLO"


def test_resolve_string_out_of_bounds():
    """Pointer beyond data length returns None."""
    data = b"\x00" * 10
    assert resolve_string(data, 0xFFFF) is None


def test_parse_cms_header():
    """Parse the 4-field CMS header."""
    header = struct.pack(">IIII", 1000, 500, 42, 10)
    header += b"\x00" * 24  # padding to 40 bytes
    result = parse_cms_header(header)
    assert result["file_size"] == 1000
    assert result["data_region_size"] == 500
    assert result["ptr1_count"] == 42
    assert result["ptr2_count"] == 10
