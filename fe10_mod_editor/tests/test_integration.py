import os
import tempfile
import shutil
import pytest
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.mod_builder import ModBuilder
from fe10_mod_editor.core.backup_manager import compute_backup_hashes
from fe10_mod_editor.core.lz10 import decompress_lz10
from fe10_mod_editor.core.item_parser import parse_all_items
from fe10_mod_editor.core.cms_parser import parse_cms_header


@pytest.fixture
def full_build_env(backup_dir):
    """Set up a complete build environment."""
    tmp = tempfile.mkdtemp()
    game_dir = os.path.join(tmp, "Game", "DATA")
    game_files = os.path.join(game_dir, "files")
    shop_out = os.path.join(game_files, "Shop")
    sys_dir = os.path.join(game_dir, "sys")
    os.makedirs(shop_out)
    os.makedirs(sys_dir)

    # Copy originals to game directory
    shutil.copy2(os.path.join(backup_dir, "FE10Data.cms"), game_files)
    for f in ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]:
        shutil.copy2(os.path.join(backup_dir, f), shop_out)
    shutil.copy2(os.path.join(backup_dir, "fst.bin"), sys_dir)

    yield {"tmp": tmp, "backup_dir": backup_dir, "game_dir": game_dir}
    shutil.rmtree(tmp)


def test_full_roundtrip_with_edits(full_build_env):
    """Build a mod with price edits and PRF removal, verify output is valid."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = full_build_env["backup_dir"]
    proj.paths["game_dir"] = full_build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(full_build_env["backup_dir"])

    # Edit Iron Sword price to 0
    proj.item_edits["IID_IRONSWORD"] = {"price": 0}
    # Enable PRF lock removal
    proj.misc["weapon_changes"]["remove_prf_locks"] = True

    log = []
    builder = ModBuilder(proj, log_callback=lambda msg: log.append(msg))
    builder.build()

    # Verify FE10Data.cms was produced
    cms_path = os.path.join(full_build_env["game_dir"], "files", "FE10Data.cms")
    assert os.path.exists(cms_path)

    # Verify shop files were produced and are valid CMS
    for suffix in ["n", "m", "h"]:
        shop_path = os.path.join(full_build_env["game_dir"], "files", "Shop", f"shopitem_{suffix}.bin")
        assert os.path.exists(shop_path)
        with open(shop_path, "rb") as f:
            shop_data = f.read()
        header = parse_cms_header(shop_data)
        assert header["file_size"] == len(shop_data)

    # Verify fst.bin was updated
    fst_path = os.path.join(full_build_env["game_dir"], "sys", "fst.bin")
    assert os.path.exists(fst_path)

    # Verify the price edit was applied
    with open(cms_path, "rb") as f:
        modded_cms = f.read()
    modded_data = decompress_lz10(modded_cms)
    items = parse_all_items(modded_data)
    iron_sword = next(i for i in items if i["iid"] == "IID_IRONSWORD")
    assert iron_sword["price"] == 0

    # Verify build log has completion message
    assert any("complete" in line.lower() for line in log)
