import os
import pytest
from fe10_mod_editor.models.skill_data import SkillEntry, SkillDatabase, display_name_from_sid


def test_display_name_from_sid():
    assert display_name_from_sid("SID_HERO") == "Hero"
    assert display_name_from_sid("SID_HOWL") == "Howl"
    assert display_name_from_sid("SID_WRATH_S") == "Wrath S"


def test_skill_entry_display_name():
    entry = SkillEntry(
        sid="SID_MIRACLE", msid="MSID_MIRACLE", capacity_cost=15, visibility=1,
    )
    assert entry.display_name == "Miracle"
    assert entry.is_visible is True


def test_skill_entry_visibility_hidden():
    entry = SkillEntry(
        sid="SID_HERO", msid="MSID_HERO", capacity_cost=0, visibility=3,
    )
    assert entry.is_visible is False


def test_skill_database_from_parsed(backup_dir):
    """Parse real data, build SkillDatabase, check count."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.skill_parser import parse_all_skills

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_skills(data)

    db = SkillDatabase.from_parsed(parsed)
    assert db.count == 142

    all_skills = db.all_skills
    assert len(all_skills) == 142

    # All entries should have the required fields
    first = all_skills[0]
    assert first.sid == "SID_HERO"
    assert isinstance(first.whitelist, list)
    assert isinstance(first.blacklist, list)


def test_skill_database_get(backup_dir):
    """Look up known SIDs."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.skill_parser import parse_all_skills

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_skills(data)
    db = SkillDatabase.from_parsed(parsed)

    howl = db.get("SID_HOWL")
    assert howl is not None
    assert howl.sid == "SID_HOWL"
    assert howl.capacity_cost == 20
    assert len(howl.whitelist) == 3

    missing = db.get("SID_DOES_NOT_EXIST")
    assert missing is None


def test_skill_database_check_restriction_no_whitelist(backup_dir):
    """A skill with no whitelist/blacklist should return None for any class."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.skill_parser import parse_all_skills

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_skills(data)
    db = SkillDatabase.from_parsed(parsed)

    # Find a skill with empty whitelist and blacklist
    open_skill = next(
        (s for s in db.all_skills if not s.whitelist and not s.blacklist),
        None
    )
    if open_skill:
        result = db.check_restriction(open_skill.sid, "JID_BRAVE")
        assert result is None


def test_skill_database_check_restriction_whitelist(backup_dir):
    """SID_HOWL has a whitelist; assigning to a non-whitelisted class returns a string."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.skill_parser import parse_all_skills

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_skills(data)
    db = SkillDatabase.from_parsed(parsed)

    # SID_HOWL is restricted to laguz beast classes — JID_BRAVE should be blocked
    result = db.check_restriction("SID_HOWL", "JID_BRAVE")
    assert isinstance(result, str), "Expected a restriction reason string"

    # Assigning to a whitelisted entry should return None
    howl = db.get("SID_HOWL")
    assert howl is not None
    if howl.whitelist:
        ok = db.check_restriction("SID_HOWL", howl.whitelist[0])
        assert ok is None


def test_skill_database_check_restriction_unknown_sid():
    """Checking an unknown SID returns an error string."""
    db = SkillDatabase([])
    result = db.check_restriction("SID_UNKNOWN", "JID_BRAVE")
    assert isinstance(result, str)
    assert "Unknown skill" in result
