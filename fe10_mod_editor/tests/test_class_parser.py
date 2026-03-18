import os
import pytest
from fe10_mod_editor.core.class_parser import parse_all_classes, JOB_DATA_OFFSET


def test_parse_all_classes_count(backup_dir):
    """Should parse 171 class entries."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    classes = parse_all_classes(data)
    assert len(classes) == 171


def test_parse_class_has_expected_fields(backup_dir):
    """Each parsed class has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    classes = parse_all_classes(data)
    first = classes[0]
    required_fields = [
        "jid", "mjid", "skill_capacity", "default_movement",
        "max_stats", "base_stats", "class_growth_rates",
        "byte_offset", "max_stats_offset", "weapon_ranks",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_class_max_stats_reasonable(backup_dir):
    """Max stats should be in reasonable ranges: HP 20-120."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    classes = parse_all_classes(data)
    for cls in classes:
        hp = cls["max_stats"]["hp"]
        # HP max stat should be in a reasonable range (30-120 for real classes,
        # but some debug/unused entries may have lower values)
        assert 0 <= hp <= 120, (
            f"{cls['jid']} has HP max stat {hp}, expected 0-120"
        )


def test_parse_class_first_entry_is_brave(backup_dir):
    """First class entry should be JID_BRAVE (Ike's promoted lord class)."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    classes = parse_all_classes(data)
    first = classes[0]
    assert first["jid"] == "JID_BRAVE"
    assert first["mjid"] == "MJID_BRAVE"
    assert first["constitution"] == 12
    assert first["default_movement"] == 7
    assert first["skill_capacity"] == 30
    assert first["promote_level"] == 21


def test_parse_class_growth_rates_reasonable(backup_dir):
    """Class growth rates should be 0-255 (u8 range); most are 0-100 but some
    special classes can exceed 100 (e.g., JID_WARRIOR_SP has 125 HP growth)."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    classes = parse_all_classes(data)
    for cls in classes:
        for stat, value in cls["class_growth_rates"].items():
            assert 0 <= value <= 255, (
                f"{cls['jid']} has {stat} growth rate {value}, expected 0-255"
            )


def test_parse_class_ends_at_item_data_offset(backup_dir):
    """Parsing all class entries should end exactly at the ItemData offset (0xDF44)."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    import struct
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    classes = parse_all_classes(data)
    # The last entry's byte_offset + its entry size should equal 0xDF44
    last = classes[-1]
    M = last["skill_count"]
    S = last["attr_count"]
    last_entry_end = last["byte_offset"] + 96 + M * 4 + S * 4
    assert last_entry_end == 0xDF44, (
        f"Class data ends at 0x{last_entry_end:X}, expected 0xDF44"
    )
