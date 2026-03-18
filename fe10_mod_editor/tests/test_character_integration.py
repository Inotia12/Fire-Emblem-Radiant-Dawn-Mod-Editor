import os
import tempfile
import shutil
import pytest
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.mod_builder import ModBuilder
from fe10_mod_editor.core.backup_manager import compute_backup_hashes
from fe10_mod_editor.core.lz10 import decompress_lz10
from fe10_mod_editor.core.character_parser import parse_all_characters
from fe10_mod_editor.core.class_parser import parse_all_classes


@pytest.fixture
def char_build_env(backup_dir):
    tmp = tempfile.mkdtemp()
    game_dir = os.path.join(tmp, "Game", "DATA")
    game_files = os.path.join(game_dir, "files")
    shop_out = os.path.join(game_files, "Shop")
    sys_dir = os.path.join(game_dir, "sys")
    os.makedirs(shop_out)
    os.makedirs(sys_dir)
    shutil.copy2(os.path.join(backup_dir, "FE10Data.cms"), game_files)
    for f in ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]:
        shutil.copy2(os.path.join(backup_dir, f), shop_out)
    shutil.copy2(os.path.join(backup_dir, "fst.bin"), sys_dir)
    yield {"tmp": tmp, "backup_dir": backup_dir, "game_dir": game_dir, "game_files": game_files}
    shutil.rmtree(tmp)


def test_character_edit_roundtrip(char_build_env):
    """Build with character edits, verify they apply correctly."""
    cms_path = os.path.join(char_build_env["backup_dir"], "FE10Data.cms")
    with open(cms_path, "rb") as f:
        orig_data = decompress_lz10(f.read())
    chars = parse_all_characters(orig_data)
    # Pick a character with "IKE" in PID
    target = next((c for c in chars if "IKE" in c["pid"]), chars[0])

    proj = ProjectFile.new()
    proj.paths["backup_dir"] = char_build_env["backup_dir"]
    proj.paths["game_dir"] = char_build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(char_build_env["backup_dir"])
    proj.character_edits[target["pid"]] = {
        "growth_rates": {"hp": 99, "str": 88},
        "stat_adjustments": {"hp": 10},
        "level": 20,
    }

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    output_cms = os.path.join(char_build_env["game_files"], "FE10Data.cms")
    with open(output_cms, "rb") as f:
        modded = decompress_lz10(f.read())
    modded_chars = parse_all_characters(modded)
    modded_target = next(c for c in modded_chars if c["pid"] == target["pid"])

    assert modded_target["growth_rates"]["hp"] == 99
    assert modded_target["growth_rates"]["str"] == 88
    assert modded_target["stat_adjustments"]["hp"] == 10
    assert modded_target["level"] == 20


def test_class_max_stat_preset(char_build_env):
    """Build with max stat preset, verify all classes updated."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = char_build_env["backup_dir"]
    proj.paths["game_dir"] = char_build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(char_build_env["backup_dir"])
    proj.misc["class_changes"] = {"set_all_max_stats": True, "max_stats_preset": 60}

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    output_cms = os.path.join(char_build_env["game_files"], "FE10Data.cms")
    with open(output_cms, "rb") as f:
        modded = decompress_lz10(f.read())
    modded_classes = parse_all_classes(modded)

    for cls in modded_classes:
        assert cls["max_stats"]["hp"] == 80  # 60 + 20
        assert cls["max_stats"]["str"] == 60
