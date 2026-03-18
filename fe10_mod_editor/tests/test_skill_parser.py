import os
import pytest
from fe10_mod_editor.core.skill_parser import parse_all_skills, SKILL_DATA_OFFSET


def test_parse_all_skills_count(backup_dir):
    """Should parse 142 skill entries."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    skills = parse_all_skills(data)
    assert len(skills) == 142


def test_parse_skill_has_expected_fields(backup_dir):
    """Each parsed skill has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    skills = parse_all_skills(data)
    first = skills[0]
    required_fields = [
        "sid", "msid", "capacity_cost", "visibility",
        "whitelist", "blacklist",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_skill_capacity_costs_reasonable(backup_dir):
    """All capacity costs should be in the range -50 to 50."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    skills = parse_all_skills(data)
    for skill in skills:
        cost = skill["capacity_cost"]
        assert -50 <= cost <= 50, (
            f"{skill['sid']} has capacity cost {cost}, expected -50 to 50"
        )


def test_parse_skill_first_entry(backup_dir):
    """First skill entry should be SID_HERO."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    skills = parse_all_skills(data)
    first = skills[0]
    assert first["sid"] == "SID_HERO"
    assert first["msid"] == "MSID_HERO"
    assert first["visibility"] == 3  # hidden
    assert first["capacity_cost"] == 0


def test_parse_skill_with_restriction_tables(backup_dir):
    """Skills with restriction tables should have populated whitelist/blacklist."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    skills = parse_all_skills(data)

    # SID_HOWL (entry 96) should have a whitelist with 3 entries
    howl = next(s for s in skills if s["sid"] == "SID_HOWL")
    assert len(howl["whitelist"]) == 3
    assert "SID_HOWL" in howl["whitelist"]
    assert howl["capacity_cost"] == 20
    assert howl["visibility"] == 1

    # SID_MIRACLE should have both whitelist and blacklist
    miracle = next(s for s in skills if s["sid"] == "SID_MIRACLE")
    assert len(miracle["whitelist"]) >= 1
    assert len(miracle["blacklist"]) >= 1


def test_parse_skill_visibility_values(backup_dir):
    """Visibility should only be 1 (visible), 2 (grayed), or 3 (hidden)."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    skills = parse_all_skills(data)
    for skill in skills:
        assert skill["visibility"] in (1, 2, 3), (
            f"{skill['sid']} has visibility {skill['visibility']}, expected 1/2/3"
        )
