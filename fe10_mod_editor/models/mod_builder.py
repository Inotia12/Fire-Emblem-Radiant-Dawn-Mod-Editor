"""Build pipeline (ModBuilder) — orchestrates full mod build.

Steps:
1. Verify backup hashes
2. Decompress FE10Data.cms from backup
3. Apply item edits (price, might, accuracy, etc.)
4. Apply misc toggles (PRF removal, valuable removal, seal steal removal)
5. Recompress with LZ10, pad to original size
6. Parse shop files from backup, resolve per-chapter inventories, rebuild
7. Update fst.bin with new shop file sizes
8. Write all output to game directory
"""

import os
import struct
from typing import Callable

from fe10_mod_editor.core.backup_manager import verify_backup_hashes
from fe10_mod_editor.core.cms_parser import resolve_string
from fe10_mod_editor.core.fst_updater import patch_fst_sizes
from fe10_mod_editor.core.item_parser import ITEM_DATA_OFFSET, parse_all_items
from fe10_mod_editor.core.lz10 import compress_lz10, decompress_lz10
from fe10_mod_editor.core.shop_builder import build_shop_file
from fe10_mod_editor.core.shop_parser import CHAPTERS, parse_shop_file
from fe10_mod_editor.models.item_data import ItemDatabase
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.shop_data import ShopDatabase

ORIGINAL_CMS_SIZE = 124288

DIFFICULTY_MAP = {"n": "normal", "m": "hard", "h": "maniac"}

# Field offsets within an item entry (relative to entry start)
FIELD_OFFSETS = {
    "price": (38, ">H"),
    "might": (40, "B"),
    "accuracy": (41, "B"),
    "critical": (42, "B"),
    "weight": (43, "B"),
    "uses": (44, "B"),
    "wexp_gain": (45, "B"),
}


class ModBuilder:
    def __init__(
        self,
        project: ProjectFile,
        log_callback: Callable[[str], None] | None = None,
    ):
        self.project = project
        self.log = log_callback or (lambda msg: None)

    def build(self):
        """Execute the full build pipeline."""
        proj = self.project
        backup_dir = proj.paths["backup_dir"]
        game_dir = proj.paths["game_dir"]
        game_files = os.path.join(game_dir, "files")
        shop_dir = os.path.join(game_files, "Shop")
        fst_path = os.path.join(game_dir, "sys", "fst.bin")

        # ------------------------------------------------------------------
        # Step 1: Verify backup hashes
        # ------------------------------------------------------------------
        self.log("Verifying backup integrity...")
        result = verify_backup_hashes(backup_dir, proj.backup_hashes)
        if not result.ok:
            raise RuntimeError(f"Backup verification failed: {result.error}")
        self.log("Backups verified.")

        # ------------------------------------------------------------------
        # Step 2: Decompress FE10Data.cms from backup
        # ------------------------------------------------------------------
        self.log("Decompressing FE10Data.cms from backup...")
        cms_backup = os.path.join(backup_dir, "FE10Data.cms")
        with open(cms_backup, "rb") as f:
            compressed = f.read()
        data = bytearray(decompress_lz10(compressed))
        self.log(f"Decompressed to {len(data)} bytes.")

        # Parse all items for reference (needed for rank pointer lookup, shop eligibility)
        parsed_items = parse_all_items(bytes(data))
        item_db = ItemDatabase.from_parsed_items(parsed_items)

        # ------------------------------------------------------------------
        # Step 3: Apply item edits
        # ------------------------------------------------------------------
        if proj.item_edits:
            self.log(f"Applying {len(proj.item_edits)} item edit(s)...")
            self._apply_item_edits(data, parsed_items, proj.item_edits)
        else:
            self.log("No item edits to apply.")

        # ------------------------------------------------------------------
        # Step 4: Apply misc toggles
        # ------------------------------------------------------------------
        misc = proj.misc.get("weapon_changes", {})
        if any(misc.values()):
            self.log("Applying misc toggles...")
            self._apply_misc_toggles(data, parsed_items, misc)
        else:
            self.log("No misc toggles enabled.")

        # ------------------------------------------------------------------
        # Step 5: Recompress with LZ10, pad to original size
        # ------------------------------------------------------------------
        self.log("Recompressing FE10Data.cms (this may take a while)...")
        recompressed = bytearray(compress_lz10(bytes(data)))
        if len(recompressed) > ORIGINAL_CMS_SIZE:
            self.log(
                f"WARNING: Recompressed size ({len(recompressed)}) exceeds "
                f"original ({ORIGINAL_CMS_SIZE}). File may not work!"
            )
        else:
            recompressed.extend(b"\x00" * (ORIGINAL_CMS_SIZE - len(recompressed)))
        cms_output = os.path.join(game_files, "FE10Data.cms")
        with open(cms_output, "wb") as f:
            f.write(recompressed)
        self.log(f"Wrote FE10Data.cms ({len(recompressed)} bytes).")

        # ------------------------------------------------------------------
        # Step 6: Rebuild shop files
        # ------------------------------------------------------------------
        self.log("Rebuilding shop files...")
        shop_sizes = {}
        for diff_key, diff_name in DIFFICULTY_MAP.items():
            shop_fname = f"shopitem_{diff_key}.bin"
            shop_backup = os.path.join(backup_dir, shop_fname)
            orig_info = parse_shop_file(shop_backup)

            # Resolve per-chapter inventories
            wshop_per_ch, ishop_per_ch = self._resolve_shop_inventories(
                item_db, orig_info, diff_name,
            )

            new_shop = build_shop_file(orig_info, wshop_per_ch, ishop_per_ch)
            out_path = os.path.join(shop_dir, shop_fname)
            with open(out_path, "wb") as f:
                f.write(new_shop)
            shop_sizes[shop_fname] = len(new_shop)
            self.log(f"  {shop_fname}: {len(new_shop)} bytes")

        # ------------------------------------------------------------------
        # Step 7: Patch fst.bin with new shop file sizes
        # ------------------------------------------------------------------
        self.log("Patching fst.bin...")
        fst_backup = os.path.join(backup_dir, "fst.bin")
        with open(fst_backup, "rb") as f:
            fst_data = f.read()
        patched_fst = patch_fst_sizes(fst_data, shop_sizes)
        with open(fst_path, "wb") as f:
            f.write(patched_fst)
        self.log("fst.bin patched.")

        # ------------------------------------------------------------------
        # Done
        # ------------------------------------------------------------------
        self.log("Build complete.")

    # ======================================================================
    # Private helpers
    # ======================================================================

    def _apply_item_edits(
        self,
        data: bytearray,
        parsed_items: list[dict],
        item_edits: dict[str, dict],
    ):
        """Apply per-item field edits to the decompressed binary."""
        items_by_iid = {item["iid"]: item for item in parsed_items}

        for iid, edits in item_edits.items():
            item = items_by_iid.get(iid)
            if item is None:
                self.log(f"  WARNING: Item '{iid}' not found, skipping.")
                continue
            pos = item["byte_offset"]

            for field, value in edits.items():
                if field == "weapon_rank":
                    self._apply_rank_edit(data, parsed_items, pos, value)
                elif field in FIELD_OFFSETS:
                    offset, fmt = FIELD_OFFSETS[field]
                    if fmt == ">H":
                        struct.pack_into(fmt, data, pos + offset, value)
                    else:
                        data[pos + offset] = value & 0xFF
                else:
                    self.log(f"  WARNING: Unknown field '{field}' for {iid}, skipping.")

    def _apply_rank_edit(
        self,
        data: bytearray,
        parsed_items: list[dict],
        item_pos: int,
        target_rank: str,
    ):
        """Change an item's weapon rank by finding the target rank's pointer."""
        target_ptr = None
        for item in parsed_items:
            if item["weapon_rank"] == target_rank:
                target_ptr = item["_rank_ptr"]
                break
        if target_ptr is None:
            self.log(f"  WARNING: Could not find rank '{target_rank}' pointer.")
            return
        struct.pack_into(">I", data, item_pos + 20, target_ptr)

    def _apply_misc_toggles(
        self,
        data: bytearray,
        parsed_items: list[dict],
        misc: dict,
    ):
        """Apply misc weapon/item toggles."""
        remove_prf = misc.get("remove_prf_locks", False)
        remove_valuable = misc.get("remove_valuable", False)
        remove_seal_steal = misc.get("remove_seal_steal", False)

        # Find rank D pointer (needed for PRF removal: N -> D)
        rank_d_ptr = None
        if remove_prf:
            for item in parsed_items:
                if item["weapon_rank"] == "D":
                    rank_d_ptr = item["_rank_ptr"]
                    break
            if rank_d_ptr is None:
                self.log("  WARNING: Could not find rank 'D' pointer. PRF rank change skipped.")

        count_rank_changed = 0
        count_eq_removed = 0
        count_valuable_removed = 0
        count_sealsteal_removed = 0

        item_count = struct.unpack(">I", data[ITEM_DATA_OFFSET:ITEM_DATA_OFFSET + 4])[0]
        pos = ITEM_DATA_OFFSET + 4

        for _ in range(item_count):
            # PRF removal: change rank N -> D and remove eq* attributes
            if remove_prf:
                if rank_d_ptr is not None:
                    rank_ptr = struct.unpack(">I", data[pos + 20:pos + 24])[0]
                    rank_str = resolve_string(data, rank_ptr)
                    if rank_str == "N":
                        struct.pack_into(">I", data, pos + 20, rank_d_ptr)
                        count_rank_changed += 1

            # Read variable-length counts
            attr_count = data[pos + 53]
            eff_count = data[pos + 54]
            prf_flag = data[pos + 55]

            # Scan attributes for removals
            for a in range(attr_count):
                attr_off = pos + 56 + (a * 4)
                attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
                attr_str = resolve_string(data, attr_ptr)
                if attr_str is None:
                    continue

                if remove_prf and attr_str.startswith("eq"):
                    struct.pack_into(">I", data, attr_off, 0x00000000)
                    count_eq_removed += 1

                if remove_valuable and attr_str == "valuable":
                    struct.pack_into(">I", data, attr_off, 0x00000000)
                    count_valuable_removed += 1

                if remove_seal_steal and attr_str == "sealsteal":
                    struct.pack_into(">I", data, attr_off, 0x00000000)
                    count_sealsteal_removed += 1

            # Advance to next entry
            entry_size = 56 + (attr_count * 4) + (eff_count * 4) + (prf_flag * 12)
            pos += entry_size

        if remove_prf:
            self.log(f"  PRF: rank N->D changed: {count_rank_changed}, eq* removed: {count_eq_removed}")
        if remove_valuable:
            self.log(f"  Valuable removed: {count_valuable_removed}")
        if remove_seal_steal:
            self.log(f"  Seal steal removed: {count_sealsteal_removed}")

    def _resolve_shop_inventories(
        self,
        item_db: ItemDatabase,
        orig_info: dict,
        difficulty: str,
    ) -> tuple[dict[str, list[str]], dict[str, list[str]]]:
        """Resolve per-chapter weapon and item lists for a given difficulty.

        Uses the ShopDatabase resolve algorithm:
        - Start with vanilla inventory from parsed shop file
        - Apply unified edits (replace entire chapter)
        - Apply difficulty-specific overrides

        If no edits exist at all, defaults to all eligible items for every chapter.
        """
        proj = self.project
        shop_edits = proj.shop_edits

        # Build a ShopDatabase from vanilla parsed data
        vanilla_weapons = orig_info["wshop_items"]
        vanilla_items = orig_info["ishop_items"]
        shop_db = ShopDatabase(vanilla_weapons, vanilla_items)

        # Load edits from project
        shop_db.load_from_dict(shop_edits)

        # Resolve per-chapter for this difficulty
        wshop_per_ch: dict[str, list[str]] = {}
        ishop_per_ch: dict[str, list[str]] = {}

        has_any_edits = bool(shop_edits.get("unified")) or bool(shop_edits.get("overrides"))

        for chapter in CHAPTERS:
            resolved = shop_db.resolve(chapter, difficulty)

            if has_any_edits:
                wshop_per_ch[chapter] = resolved["weapons"]
                ishop_per_ch[chapter] = resolved["items"]
            else:
                # Default: all eligible items if no edits specified
                wshop_per_ch[chapter] = [i.iid for i in item_db.weapon_shop_items]
                ishop_per_ch[chapter] = [i.iid for i in item_db.item_shop_items]

        return wshop_per_ch, ishop_per_ch
