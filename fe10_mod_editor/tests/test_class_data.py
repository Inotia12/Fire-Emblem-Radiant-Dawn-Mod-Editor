import os
import pytest
from fe10_mod_editor.models.class_data import ClassEntry, ClassDatabase, display_name_from_jid


def test_display_name_from_jid():
    assert display_name_from_jid("JID_BRAVE") == "Brave"
    assert display_name_from_jid("JID_SWORDMASTER_F") == "Swordmaster F"
    assert display_name_from_jid("JID_KINGLION") == "Kinglion"


def test_class_entry_display_name():
    entry = ClassEntry(
        jid="JID_GLORYKNIGHT", mjid="MJID_GLORYKNIGHT",
        weapon_ranks="", constitution=10, skill_capacity=20, default_movement=7,
    )
    assert entry.display_name == "Gloryknight"


def test_class_database_from_parsed(backup_dir):
    """Parse real data, build ClassDatabase, check count and field presence."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.class_parser import parse_all_classes

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_classes(data)

    db = ClassDatabase.from_parsed(parsed)
    # The game has a fixed set of classes; accept a reasonable range
    assert db.count > 50, f"Expected > 50 classes, got {db.count}"

    all_classes = db.all_classes
    assert len(all_classes) == db.count

    # Each entry should have max_stats with 8 stat keys
    first = all_classes[0]
    for stat in ("hp", "str", "mag", "skl", "spd", "lck", "def", "res"):
        assert stat in first.max_stats, f"Missing max_stats key: {stat}"
        assert stat in first.base_stats, f"Missing base_stats key: {stat}"
        assert stat in first.class_growth_rates, f"Missing class_growth_rates key: {stat}"


def test_class_database_get(backup_dir):
    """Look up a known JID."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.class_parser import parse_all_classes

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_classes(data)
    db = ClassDatabase.from_parsed(parsed)

    brave = db.get("JID_BRAVE")
    assert brave is not None
    assert brave.jid == "JID_BRAVE"
    assert isinstance(brave.max_stats, dict)
    assert brave.max_stats_offset > 0

    missing = db.get("JID_DOES_NOT_EXIST")
    assert missing is None


def test_class_max_stats_values_reasonable(backup_dir):
    """Max stats should be unsigned bytes (0-255); typical cap values 20-80."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.class_parser import parse_all_classes

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_classes(data)
    db = ClassDatabase.from_parsed(parsed)

    for cls in db.all_classes:
        for stat, val in cls.max_stats.items():
            assert 0 <= val <= 255, f"{cls.jid} max_stats[{stat}]={val} out of range"
