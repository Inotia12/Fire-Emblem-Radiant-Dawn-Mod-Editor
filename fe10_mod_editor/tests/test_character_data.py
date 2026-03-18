import os
import pytest
from fe10_mod_editor.models.character_data import (
    CharacterEntry,
    CharacterDatabase,
    display_name_from_pid,
    ALLIED_PIDS,
)


def test_display_name_from_pid():
    assert display_name_from_pid("PID_MICAIAH") == "Micaiah"
    assert display_name_from_pid("PID_IKE") == "Ike"
    assert display_name_from_pid("PID_SOANEVALCKE") == "Soanevalcke"


def test_character_entry_display_name():
    entry = CharacterEntry(
        pid="PID_SOTHE", mpid="MPID_SOTHE", jid="JID_ROGUE",
        level=1, gender=1, skill_count=0,
    )
    assert entry.display_name == "Sothe"


def test_character_entry_is_laguz_false():
    entry = CharacterEntry(
        pid="PID_IKE", mpid="MPID_IKE", jid="JID_BRAVE",
        level=11, gender=1, skill_count=0,
        laguz_gauge={"gain_turn": 0, "gain_battle": 0, "loss_turn": 0, "loss_battle": 0},
    )
    assert entry.is_laguz is False


def test_character_entry_is_laguz_true():
    entry = CharacterEntry(
        pid="PID_CAINEGHIS", mpid="MPID_CAINEGHIS", jid="JID_KINGLION",
        level=36, gender=1, skill_count=0,
        laguz_gauge={"gain_turn": 5, "gain_battle": 10, "loss_turn": -2, "loss_battle": -4},
    )
    assert entry.is_laguz is True


def test_character_database_from_parsed(backup_dir):
    """Parse real data, build database, check total count and allied count."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.character_parser import parse_all_characters

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_characters(data)

    db = CharacterDatabase.from_parsed(parsed)
    assert db.count == 461

    allied = db.allied_characters
    # The allied list should be a subset of ALLIED_PIDS that exist in the binary.
    # Some PIDs in ALLIED_PIDS may not be present in every binary (DLC / unused slots),
    # so accept any count in the range 40–70.
    assert 40 <= len(allied) <= 70, f"Expected 40-70 allied chars, got {len(allied)}"

    # All returned entries must have their PID in ALLIED_PIDS
    for c in allied:
        assert c.pid in ALLIED_PIDS, f"{c.pid} is not in ALLIED_PIDS"


def test_character_database_get(backup_dir):
    """Look up a known PID by name."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.character_parser import parse_all_characters

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_characters(data)
    db = CharacterDatabase.from_parsed(parsed)

    ike = db.get("PID_IKE")
    assert ike is not None
    assert ike.pid == "PID_IKE"
    assert ike.jid.startswith("JID_")

    missing = db.get("PID_DOES_NOT_EXIST")
    assert missing is None


def test_character_database_laguz(backup_dir):
    """Laguz characters should have non-zero gauge values; beorc should not."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.character_parser import parse_all_characters

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())
    parsed = parse_all_characters(data)
    db = CharacterDatabase.from_parsed(parsed)

    laguz = db.laguz_characters
    beorc = db.beorc_characters

    assert len(laguz) > 0
    assert len(beorc) > 0
    assert len(laguz) + len(beorc) == db.count

    caineghis = db.get("PID_CAINEGHIS")
    if caineghis:
        assert caineghis.is_laguz

    ike = db.get("PID_IKE")
    if ike:
        assert not ike.is_laguz
