import os
import pytest
from fe10_mod_editor.core.character_parser import parse_all_characters, PERSON_DATA_OFFSET


def test_parse_all_characters_count(backup_dir):
    """Parse real FE10Data and expect 461 character entries."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    characters = parse_all_characters(data)
    assert len(characters) == 461


def test_parse_character_has_expected_fields(backup_dir):
    """Each parsed character has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    characters = parse_all_characters(data)
    first = characters[0]
    required_fields = [
        "pid", "mpid", "jid", "affinity", "level", "gender",
        "skill_ids", "biorhythm_type", "playability_flag",
        "authority_stars", "laguz_gauge", "stat_adjustments",
        "growth_rates", "byte_offset", "skill_count",
        "skill_slot_offsets",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_finds_playable_characters(backup_dir):
    """Characters with non-zero playability_flag are laguz with a gauge transform threshold.
    In FE10 there are ~35 such characters (3/7/15/31 corresponding to raven/hawk/dragon etc).
    """
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    characters = parse_all_characters(data)
    playable = [c for c in characters if c["playability_flag"] != 0]
    assert len(playable) >= 10
    assert len(playable) <= 50
