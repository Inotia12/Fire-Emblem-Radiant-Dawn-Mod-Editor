import os
import pytest
from fe10_mod_editor.core.item_parser import parse_all_items, ITEM_DATA_OFFSET


def test_parse_all_items_returns_296(backup_dir):
    """Parse the real FE10Data and expect 296 items."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)

    items = parse_all_items(data)
    assert len(items) == 296


def test_parse_item_has_expected_fields(backup_dir):
    """Each parsed item has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)

    items = parse_all_items(data)
    first = items[0]

    required_fields = [
        "iid", "weapon_type", "weapon_rank", "price", "might", "accuracy",
        "critical", "weight", "uses", "wexp_gain", "min_range", "max_range",
        "attributes", "effectiveness_count", "prf_flag", "icon_id",
        "byte_offset", "display_type",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_items_finds_iron_sword(backup_dir):
    """Verify IID_IRON_SWORD is parsed with expected stats."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)

    items = parse_all_items(data)
    iron_sword = next((i for i in items if i["iid"] == "IID_IRONSWORD"), None)
    assert iron_sword is not None
    assert iron_sword["weapon_type"] == "sword"
    assert iron_sword["weapon_rank"] in ("E", "D", "C", "B", "A", "S", "N")
    assert iron_sword["might"] > 0
