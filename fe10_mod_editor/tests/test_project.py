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
