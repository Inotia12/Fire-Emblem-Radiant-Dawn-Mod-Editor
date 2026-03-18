import os
import struct
import tempfile
import shutil
import pytest
from fe10_mod_editor.models.mod_builder import ModBuilder
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.core.backup_manager import compute_backup_hashes


@pytest.fixture
def build_env(backup_dir):
    """Create a temporary game directory structure for build testing."""
    tmp = tempfile.mkdtemp()
    game_dir = os.path.join(tmp, "Game", "DATA")
    game_files = os.path.join(game_dir, "files")
    shop_out = os.path.join(game_files, "Shop")
    sys_dir = os.path.join(game_dir, "sys")
    os.makedirs(shop_out)
    os.makedirs(sys_dir)

    # Copy backup files to game directory as starting state
    shutil.copy2(os.path.join(backup_dir, "FE10Data.cms"), game_files)
    for fname in ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]:
        shutil.copy2(os.path.join(backup_dir, fname), shop_out)
    shutil.copy2(os.path.join(backup_dir, "fst.bin"), sys_dir)

    yield {
        "tmp": tmp,
        "backup_dir": backup_dir,
        "game_dir": game_dir,
        "game_files": game_files,
        "shop_dir": shop_out,
        "fst_path": os.path.join(sys_dir, "fst.bin"),
    }

    shutil.rmtree(tmp)


def test_mod_builder_runs_without_error(build_env):
    """Build with no edits should succeed."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = build_env["backup_dir"]
    proj.paths["game_dir"] = build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(build_env["backup_dir"])

    log_lines = []
    builder = ModBuilder(proj, log_callback=lambda msg: log_lines.append(msg))
    builder.build()

    assert len(log_lines) > 0
    assert any("complete" in line.lower() for line in log_lines)


def test_mod_builder_applies_price_edit(build_env):
    """Build with a price edit should produce modified FE10Data."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = build_env["backup_dir"]
    proj.paths["game_dir"] = build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(build_env["backup_dir"])
    proj.item_edits["IID_IRONSWORD"] = {"price": 0}

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    output_cms = os.path.join(build_env["game_files"], "FE10Data.cms")
    assert os.path.exists(output_cms)
    assert os.path.getsize(output_cms) > 0


def test_mod_builder_applies_character_growth_edit(build_env):
    """Build with a character growth edit should modify FE10Data."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.character_parser import parse_all_characters

    proj = ProjectFile.new()
    proj.paths["backup_dir"] = build_env["backup_dir"]
    proj.paths["game_dir"] = build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(build_env["backup_dir"])

    cms_path = os.path.join(build_env["backup_dir"], "FE10Data.cms")
    with open(cms_path, "rb") as f:
        orig_data = decompress_lz10(f.read())
    chars = parse_all_characters(orig_data)
    # Pick a character with known PID
    target = next((c for c in chars if "IKE" in c["pid"]), chars[0])
    target_pid = target["pid"]

    proj.character_edits[target_pid] = {"growth_rates": {"hp": 99}}

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    output_cms = os.path.join(build_env["game_files"], "FE10Data.cms")
    with open(output_cms, "rb") as f:
        modded_data = decompress_lz10(f.read())
    modded_chars = parse_all_characters(modded_data)
    modded_char = next(c for c in modded_chars if c["pid"] == target_pid)
    assert modded_char["growth_rates"]["hp"] == 99
