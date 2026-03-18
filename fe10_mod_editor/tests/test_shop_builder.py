import os
import struct
import pytest
from fe10_mod_editor.core.shop_builder import build_shop_file
from fe10_mod_editor.core.shop_parser import parse_shop_file
from fe10_mod_editor.core.cms_parser import parse_cms_header


def test_build_shop_file_produces_valid_cms(backup_dir):
    """Build a shop file and verify the CMS header is consistent."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    orig_info = parse_shop_file(shop_path)

    # Use a small subset of items for speed
    wshop = ["IID_IRONSWORD", "IID_STEELSWORD"]
    ishop = ["IID_VULNERARY"]

    result = build_shop_file(orig_info, wshop, ishop)
    header = parse_cms_header(result)

    assert header["file_size"] == len(result)
    assert header["ptr1_count"] > 0
    assert header["ptr2_count"] > 0


def test_build_shop_file_roundtrip(backup_dir):
    """Build a shop file, then parse it back — subsection labels should match."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    orig_info = parse_shop_file(shop_path)

    wshop = ["IID_IRONSWORD"]
    ishop = ["IID_VULNERARY"]

    result = build_shop_file(orig_info, wshop, ishop)

    # Write to temp file and parse back
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(result)
        tmp_path = f.name

    try:
        parsed_back = parse_shop_file(tmp_path)
        # Should have same chapters in WSHOP
        assert set(parsed_back["wshop_items"].keys()) == set(orig_info["wshop_items"].keys())
        # Each chapter should have our 1 weapon
        for ch_items in parsed_back["wshop_items"].values():
            assert ch_items == ["IID_IRONSWORD"]
    finally:
        os.unlink(tmp_path)


def test_build_shop_file_per_chapter_dicts(backup_dir):
    """Build with per-chapter item dicts instead of flat lists."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    orig_info = parse_shop_file(shop_path)

    # Give C0000 one weapon, C0101 two weapons
    chapters = orig_info["chapters"]
    wshop = {ch: ["IID_IRONSWORD"] for ch in chapters}
    wshop["C0101"] = ["IID_IRONSWORD", "IID_STEELSWORD"]
    ishop = {ch: ["IID_VULNERARY"] for ch in chapters}

    result = build_shop_file(orig_info, wshop, ishop)
    header = parse_cms_header(result)
    assert header["file_size"] == len(result)

    # Parse back and verify per-chapter differences
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(result)
        tmp_path = f.name
    try:
        parsed_back = parse_shop_file(tmp_path)
        assert parsed_back["wshop_items"]["C0000"] == ["IID_IRONSWORD"]
        assert parsed_back["wshop_items"]["C0101"] == ["IID_IRONSWORD", "IID_STEELSWORD"]
    finally:
        os.unlink(tmp_path)
