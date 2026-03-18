import json
import pytest
from fe10_mod_editor.models.project import ProjectFile


def test_project_new_creates_defaults():
    proj = ProjectFile.new()
    assert proj.version == 1
    assert proj.item_edits == {}
    assert proj.misc["weapon_changes"]["remove_prf_locks"] is False


def test_project_save_and_load(tmp_path):
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = "/some/backup"
    proj.item_edits["IID_IRONSWORD"] = {"price": 0, "might": 12}
    proj.misc["weapon_changes"]["remove_prf_locks"] = True

    path = str(tmp_path / "test.fe10mod")
    proj.save(path)

    loaded = ProjectFile.load(path)
    assert loaded.paths["backup_dir"] == "/some/backup"
    assert loaded.item_edits["IID_IRONSWORD"]["price"] == 0
    assert loaded.misc["weapon_changes"]["remove_prf_locks"] is True


def test_project_file_is_valid_json(tmp_path):
    proj = ProjectFile.new()
    path = str(tmp_path / "test.fe10mod")
    proj.save(path)

    with open(path) as f:
        data = json.load(f)
    assert data["version"] == 1
    assert "paths" in data


def test_project_shop_edits_roundtrip(tmp_path):
    proj = ProjectFile.new()
    proj.shop_edits = {
        "unified": {"C0101": {"weapons": ["IID_A"]}},
        "overrides": {"hard": {"C0101": {"weapons": ["IID_B"]}}},
    }

    path = str(tmp_path / "test.fe10mod")
    proj.save(path)
    loaded = ProjectFile.load(path)

    assert loaded.shop_edits["unified"]["C0101"]["weapons"] == ["IID_A"]
    assert loaded.shop_edits["overrides"]["hard"]["C0101"]["weapons"] == ["IID_B"]


def test_project_new_has_character_and_class_fields():
    """New project should have character_edits, class_max_stat_edits, and misc.class_changes."""
    proj = ProjectFile.new()
    assert proj.character_edits == {}
    assert proj.class_max_stat_edits == {}
    assert "class_changes" in proj.misc
    assert proj.misc["class_changes"]["set_all_max_stats"] is False
    assert proj.misc["class_changes"]["max_stats_preset"] == 40


def test_project_character_edits_roundtrip(tmp_path):
    """character_edits and class_max_stat_edits survive a save/load roundtrip."""
    proj = ProjectFile.new()
    proj.character_edits["PID_IKE"] = {"level": 20, "growth_rates": {"hp": 60}}
    proj.class_max_stat_edits["JID_BRAVE"] = {"hp": 80, "str": 40}

    path = str(tmp_path / "test_chars.fe10mod")
    proj.save(path)
    loaded = ProjectFile.load(path)

    assert loaded.character_edits["PID_IKE"]["level"] == 20
    assert loaded.character_edits["PID_IKE"]["growth_rates"]["hp"] == 60
    assert loaded.class_max_stat_edits["JID_BRAVE"]["hp"] == 80
    assert loaded.class_max_stat_edits["JID_BRAVE"]["str"] == 40


def test_project_misc_class_changes_roundtrip(tmp_path):
    """misc.class_changes survives a save/load roundtrip."""
    proj = ProjectFile.new()
    proj.misc["class_changes"]["set_all_max_stats"] = True
    proj.misc["class_changes"]["max_stats_preset"] = 60

    path = str(tmp_path / "test_class_misc.fe10mod")
    proj.save(path)
    loaded = ProjectFile.load(path)

    assert loaded.misc["class_changes"]["set_all_max_stats"] is True
    assert loaded.misc["class_changes"]["max_stats_preset"] == 60


def test_project_load_old_file_without_new_fields(tmp_path):
    """Loading an old project file that lacks the new fields should use defaults."""
    import json
    old_data = {
        "version": 1,
        "paths": {"backup_dir": "/old/path", "game_dir": ""},
        "backup_hashes": {},
        "item_edits": {},
        "shop_edits": {"unified": {}, "overrides": {}},
        "misc": {
            "weapon_changes": {
                "remove_prf_locks": False,
                "remove_valuable": False,
                "remove_seal_steal": False,
            }
        },
    }
    path = str(tmp_path / "old.fe10mod")
    with open(path, "w") as f:
        json.dump(old_data, f)

    loaded = ProjectFile.load(path)
    assert loaded.character_edits == {}
    assert loaded.class_max_stat_edits == {}
    assert loaded.misc["weapon_changes"]["remove_prf_locks"] is False
    # class_changes should come from defaults (merged during __init__)
    assert "class_changes" in loaded.misc
    assert loaded.misc["class_changes"]["set_all_max_stats"] is False
