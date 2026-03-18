"""
Fire Emblem: Radiant Dawn - Free All Items Shop Mod
====================================================

This script applies a complete mod to Fire Emblem: Radiant Dawn game data in
three sequential steps:

  Part 1 - Modify FE10Data.cms:
           * Zero all 296 item prices so everything costs 0 gold.
           * Remove "sealsteal" attributes (prevents theft-lock on items).
           * Remove "valuable" attributes (prevents items from being flagged
             as non-discardable/valuable).
           * Remove "eq*" attributes (removes equip-lock restrictions).
           * Change rank "N" to rank "D" (makes items usable at base rank).
           * Save the decompressed modified data for the shop rebuild step.
           * Recompress with LZ10, padded to original file size (124288 bytes).

  Part 2 - Rebuild the three shop inventory files (shopitem_n.bin,
           shopitem_m.bin, shopitem_h.bin) so that every chapter's weapon
           shop and item shop stock ALL available items in the game.
           Delegates to rebuild_randomizer_style.py as a subprocess.

  Part 3 - Update the File System Table (fst.bin) with the new sizes of
           the three rebuilt shop files so the game loads them correctly.

Paths:
  - Game files live under Game/DATA/ relative to this script's directory.
  - Original backups are stored in Backup/ and are never overwritten.

Usage:
  python mod_free_shop.py
"""

import struct
import os
import sys
import shutil
import subprocess


# ---------------------------------------------------------------------------
# Path setup - all paths relative to this script's directory
# ---------------------------------------------------------------------------
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))

GAME_DATA_FILES = os.path.join(SCRIPT_DIR, "Game", "DATA", "files")
GAME_DATA_SYS   = os.path.join(SCRIPT_DIR, "Game", "DATA", "sys")
BACKUP_DIR       = os.path.join(SCRIPT_DIR, "Backup")

FE10DATA_CMS     = os.path.join(GAME_DATA_FILES, "FE10Data.cms")
FE10DATA_DECOMP  = os.path.join(GAME_DATA_FILES, "FE10Data_decompressed.bin")
SHOP_DIR         = os.path.join(GAME_DATA_FILES, "Shop")
FST_PATH         = os.path.join(GAME_DATA_SYS, "fst.bin")

SHOP_FILES       = ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]

# FST entry indices for the shop files (each FST entry is 12 bytes)
FST_SHOP_INDICES = {
    "shopitem_h.bin": 1788,
    "shopitem_m.bin": 1789,
    "shopitem_n.bin": 1790,
}

# Original compressed FE10Data.cms file size (must pad recompressed to this)
ORIGINAL_CMS_SIZE = 124288


# ---------------------------------------------------------------------------
# Safe print helper - avoids Unicode errors on Windows consoles
# ---------------------------------------------------------------------------
def safe_print(msg):
    """Print a message safely, handling potential Unicode encoding issues."""
    try:
        sys.stdout.buffer.write((msg + "\n").encode("utf-8", errors="replace"))
        sys.stdout.buffer.flush()
    except Exception:
        print(msg)


# ---------------------------------------------------------------------------
# Backup helper
# ---------------------------------------------------------------------------
def backup_file(filepath, backup_dir):
    """Copy filepath into backup_dir if a backup does not already exist there.

    Returns the path to the backup file.
    """
    os.makedirs(backup_dir, exist_ok=True)
    basename = os.path.basename(filepath)
    bak_path = os.path.join(backup_dir, basename)
    if not os.path.exists(bak_path):
        shutil.copy2(filepath, bak_path)
        safe_print(f"  Backed up: {basename} -> Backup/{basename}")
    else:
        safe_print(f"  Backup already exists: Backup/{basename}")
    return bak_path


# ===========================================================================
# LZ10 Decompression
# ===========================================================================
def decompress_lz10(data):
    """Decompress an LZ10-compressed byte string.

    LZ10 header: byte 0 = 0x10, bytes 1-3 = decompressed size (LE, 24-bit).
    """
    if data[0] != 0x10:
        raise ValueError("Not LZ10 compressed (first byte != 0x10)")

    decomp_size = struct.unpack('<I', data[1:4] + b'\x00')[0]
    output = bytearray()
    pos = 4

    while len(output) < decomp_size and pos < len(data):
        flags = data[pos]; pos += 1
        for bit in range(8):
            if len(output) >= decomp_size:
                break
            if flags & (0x80 >> bit):
                # Back-reference
                if pos + 1 >= len(data):
                    break
                b1, b2 = data[pos], data[pos + 1]; pos += 2
                length = ((b1 >> 4) & 0x0F) + 3
                offset = ((b1 & 0x0F) << 8) | b2
                offset += 1
                for _ in range(length):
                    if len(output) >= decomp_size:
                        break
                    output.append(output[-offset])
            else:
                # Literal byte
                if pos >= len(data):
                    break
                output.append(data[pos]); pos += 1

    return bytes(output[:decomp_size])


# ===========================================================================
# LZ10 Compression
# ===========================================================================
def compress_lz10(data):
    """Compress a byte string using LZ10 (brute-force sliding window)."""
    output = bytearray()
    size = len(data)

    # 4-byte header: 0x10 tag + 24-bit decompressed size (LE)
    output.append(0x10)
    output.append(size & 0xFF)
    output.append((size >> 8) & 0xFF)
    output.append((size >> 16) & 0xFF)

    pos = 0
    while pos < len(data):
        flag_byte_pos = len(output)
        output.append(0)
        flags = 0

        for bit in range(8):
            if pos >= len(data):
                break

            best_len = 0
            best_off = 0
            max_search = min(pos, 4096)
            max_len = min(len(data) - pos, 18)

            for off in range(1, max_search + 1):
                match_len = 0
                while (match_len < max_len and
                       data[pos + match_len] == data[pos - off + (match_len % off)]):
                    match_len += 1
                if match_len >= 3 and match_len > best_len:
                    best_len = match_len
                    best_off = off
                    if best_len == 18:
                        break

            if best_len >= 3:
                flags |= (0x80 >> bit)
                b1 = ((best_len - 3) << 4) | (((best_off - 1) >> 8) & 0x0F)
                b2 = (best_off - 1) & 0xFF
                output.append(b1)
                output.append(b2)
                pos += best_len
            else:
                output.append(data[pos])
                pos += 1

        output[flag_byte_pos] = flags

    return bytes(output)


# ===========================================================================
# CMS string resolver
# ===========================================================================
def resolve_string(data, ptr):
    """Resolve a CMS string pointer to a Python string.

    CMS convention: stored pointer + 0x20 = actual file offset of the
    null-terminated ASCII string.  Returns None if ptr is 0 or string empty.
    """
    if ptr == 0:
        return None
    offset = ptr + 0x20
    if offset >= len(data) or data[offset] == 0:
        return None
    end = data.index(0, offset)
    return data[offset:end].decode("ascii", errors="replace")


# ===========================================================================
# Part 1 -- Modify FE10Data.cms
# ===========================================================================
def modify_fe10data():
    """Decompress FE10Data.cms and apply all item modifications:
      - Zero every item price
      - Remove sealsteal, valuable, and eq* attributes
      - Change rank N to rank D
    Then save decompressed data and recompress back to FE10Data.cms.

    Returns a dict of modification counts for the summary report.
    """
    safe_print("=" * 60)
    safe_print("Part 1: Modifying item data in FE10Data.cms")
    safe_print("=" * 60)

    # --- Verify source file exists ---
    if not os.path.exists(FE10DATA_CMS):
        raise FileNotFoundError(f"Cannot find {FE10DATA_CMS}")

    # --- Create backup (into Backup/ directory, never overwrite) ---
    bak_path = backup_file(FE10DATA_CMS, BACKUP_DIR)

    # --- Always decompress from the BACKUP (the clean original) ---
    with open(bak_path, "rb") as f:
        compressed = f.read()
    safe_print(f"  Read {len(compressed)} bytes from backup.")

    data = bytearray(decompress_lz10(compressed))
    safe_print(f"  Decompressed to {len(data)} bytes.")

    # --- Parse ItemData section ---
    ITEM_DATA_OFFSET = 0xDF44
    item_count = struct.unpack(">I", data[ITEM_DATA_OFFSET:ITEM_DATA_OFFSET + 4])[0]
    safe_print(f"  ItemData count: {item_count} entries")

    # --- First pass: find the pointer value for rank "D" ---
    # We need this to replace rank "N" pointers.  Scan all items and find
    # one whose rank string is "D", then use its rank pointer value.
    rank_d_ptr = None
    pos = ITEM_DATA_OFFSET + 4
    for _ in range(item_count):
        rank_ptr = struct.unpack(">I", data[pos + 20:pos + 24])[0]
        rank_str = resolve_string(data, rank_ptr)
        if rank_str == "D":
            rank_d_ptr = rank_ptr
            break
        ac = data[pos + 53]
        ec = data[pos + 54]
        pf = data[pos + 55]
        pos += 56 + (ac * 4) + (ec * 4) + (pf * 12)

    if rank_d_ptr is None:
        safe_print("  WARNING: Could not find any item with rank 'D'.")
        safe_print("           Rank N->D conversion will be skipped.")
    else:
        safe_print(f"  Found rank 'D' pointer value: 0x{rank_d_ptr:08X}")

    # --- Second pass: apply all modifications ---
    count_prices_zeroed = 0
    count_sealsteal_removed = 0
    count_valuable_removed = 0
    count_eq_removed = 0
    count_rank_changed = 0

    pos = ITEM_DATA_OFFSET + 4
    for i in range(item_count):
        # --- Zero the price (2-byte BE u16 at entry offset +38) ---
        cost_offset = pos + 38
        old_cost = struct.unpack(">H", data[cost_offset:cost_offset + 2])[0]
        if old_cost != 0:
            struct.pack_into(">H", data, cost_offset, 0)
            count_prices_zeroed += 1

        # --- Change rank N to D (4-byte pointer at entry offset +20) ---
        if rank_d_ptr is not None:
            rank_ptr = struct.unpack(">I", data[pos + 20:pos + 24])[0]
            rank_str = resolve_string(data, rank_ptr)
            if rank_str == "N":
                struct.pack_into(">I", data, pos + 20, rank_d_ptr)
                count_rank_changed += 1

        # --- Remove sealsteal, valuable, and eq* attributes ---
        ac = data[pos + 53]   # attribute count
        ec = data[pos + 54]   # effectiveness count
        pf = data[pos + 55]   # proficiency count

        for a in range(ac):
            attr_off = pos + 56 + (a * 4)
            attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
            attr_str = resolve_string(data, attr_ptr)
            if attr_str is None:
                continue

            if attr_str == "sealsteal":
                struct.pack_into(">I", data, attr_off, 0x00000000)
                count_sealsteal_removed += 1
            elif attr_str == "valuable":
                struct.pack_into(">I", data, attr_off, 0x00000000)
                count_valuable_removed += 1
            elif attr_str.startswith("eq"):
                struct.pack_into(">I", data, attr_off, 0x00000000)
                count_eq_removed += 1

        # --- Advance to next variable-length entry ---
        entry_size = 56 + (ac * 4) + (ec * 4) + (pf * 12)
        pos += entry_size

    # --- Report counts ---
    safe_print(f"  Prices zeroed:       {count_prices_zeroed} / {item_count}")
    safe_print(f"  Sealsteal removed:   {count_sealsteal_removed}")
    safe_print(f"  Valuable removed:    {count_valuable_removed}")
    safe_print(f"  eq* removed:         {count_eq_removed}")
    safe_print(f"  Rank N -> D changed: {count_rank_changed}")

    # --- Save decompressed data (needed by Part 2's shop rebuild) ---
    with open(FE10DATA_DECOMP, "wb") as f:
        f.write(data)
    safe_print(f"  Wrote decompressed data to FE10Data_decompressed.bin")

    # --- Recompress and pad to original file size ---
    safe_print("  Recompressing with LZ10 (this may take a few minutes)...")
    recompressed = bytearray(compress_lz10(bytes(data)))

    if len(recompressed) > ORIGINAL_CMS_SIZE:
        safe_print(f"  WARNING: Recompressed size ({len(recompressed)}) exceeds "
                    f"original ({ORIGINAL_CMS_SIZE}). File may not work!")
    else:
        # Pad with zero bytes to match original size
        recompressed.extend(b'\x00' * (ORIGINAL_CMS_SIZE - len(recompressed)))

    with open(FE10DATA_CMS, "wb") as f:
        f.write(recompressed)
    safe_print(f"  Wrote {len(recompressed)} bytes to FE10Data.cms "
               f"(padded to {ORIGINAL_CMS_SIZE})")
    safe_print("  Part 1 complete.\n")

    return {
        "prices_zeroed": count_prices_zeroed,
        "sealsteal_removed": count_sealsteal_removed,
        "valuable_removed": count_valuable_removed,
        "eq_removed": count_eq_removed,
        "rank_changed": count_rank_changed,
    }


# ===========================================================================
# Part 2 -- Rebuild shop files (delegates to rebuild_randomizer_style.py)
# ===========================================================================
def rebuild_shops():
    """Rebuild all three shop files by running rebuild_randomizer_style.py.

    That script reads FE10Data_decompressed.bin (written by Part 1) and the
    original shop backups from Backup/, producing new shopitem_n/m/h.bin
    files in Game/DATA/files/Shop/.
    """
    safe_print("=" * 60)
    safe_print("Part 2: Rebuilding shop files with all items")
    safe_print("=" * 60)

    # Verify prerequisites
    if not os.path.exists(FE10DATA_DECOMP):
        raise FileNotFoundError(
            f"Cannot find {FE10DATA_DECOMP} -- run Part 1 first.")

    rebuild_script = os.path.join(SCRIPT_DIR, "rebuild_randomizer_style.py")
    if not os.path.exists(rebuild_script):
        raise FileNotFoundError(
            f"Cannot find {rebuild_script}")

    # Ensure shop backup files exist
    for fname in SHOP_FILES:
        shop_src = os.path.join(SHOP_DIR, fname)
        if not os.path.exists(shop_src):
            raise FileNotFoundError(f"Cannot find {shop_src}")
        backup_file(shop_src, BACKUP_DIR)

    # Run the rebuild script as a subprocess
    safe_print(f"  Running rebuild_randomizer_style.py...")
    result = subprocess.run(
        [sys.executable, rebuild_script],
        capture_output=True,
        text=True,
    )

    # Print its output
    if result.stdout:
        for line in result.stdout.strip().split("\n"):
            safe_print(f"    {line}")
    if result.returncode != 0:
        safe_print(f"  ERROR: rebuild script exited with code {result.returncode}")
        if result.stderr:
            for line in result.stderr.strip().split("\n"):
                safe_print(f"    STDERR: {line}")
        raise RuntimeError("Shop rebuild failed.")

    # Report rebuilt file sizes
    for fname in SHOP_FILES:
        fpath = os.path.join(SHOP_DIR, fname)
        fsize = os.path.getsize(fpath)
        safe_print(f"  {fname}: {fsize} bytes")

    safe_print("  Part 2 complete.\n")


# ===========================================================================
# Part 3 -- Update FST with new shop file sizes
# ===========================================================================
def update_fst():
    """Read fst.bin, update the size fields for the three shop file entries
    to match the actual sizes of the rebuilt shop files, and write it back.

    FST entry format (12 bytes each):
      - Bytes 0-3: name offset (or flags for root)
      - Bytes 4-7: file offset on disc
      - Bytes 8-11: file size (big-endian u32)

    The size field at bytes 8-11 of each 12-byte entry must match the
    actual file size of the corresponding shop file.
    """
    safe_print("=" * 60)
    safe_print("Part 3: Updating FST (File System Table)")
    safe_print("=" * 60)

    if not os.path.exists(FST_PATH):
        raise FileNotFoundError(f"Cannot find {FST_PATH}")

    # Backup FST
    backup_file(FST_PATH, BACKUP_DIR)

    # Read FST
    with open(FST_PATH, "rb") as f:
        fst_data = bytearray(f.read())

    safe_print(f"  Read {len(fst_data)} bytes from fst.bin")

    # Update each shop file's size entry
    for fname, entry_index in FST_SHOP_INDICES.items():
        shop_path = os.path.join(SHOP_DIR, fname)
        if not os.path.exists(shop_path):
            raise FileNotFoundError(f"Cannot find rebuilt shop file: {shop_path}")

        actual_size = os.path.getsize(shop_path)

        # FST entry offset: entry_index * 12, size field at bytes 8-11
        entry_offset = entry_index * 12
        size_offset = entry_offset + 8

        old_size = struct.unpack(">I", fst_data[size_offset:size_offset + 4])[0]
        struct.pack_into(">I", fst_data, size_offset, actual_size)

        safe_print(f"  {fname} (index {entry_index}): "
                    f"{old_size} -> {actual_size} bytes")

    # Write updated FST
    with open(FST_PATH, "wb") as f:
        f.write(fst_data)
    safe_print(f"  Wrote updated fst.bin ({len(fst_data)} bytes)")
    safe_print("  Part 3 complete.\n")


# ===========================================================================
# Main entry point
# ===========================================================================
def main():
    safe_print("")
    safe_print("Fire Emblem: Radiant Dawn -- Free All Items Shop Mod")
    safe_print("=" * 60)
    safe_print("")

    # Verify directory structure exists
    for d in [GAME_DATA_FILES, GAME_DATA_SYS, SHOP_DIR]:
        if not os.path.isdir(d):
            raise FileNotFoundError(f"Required directory not found: {d}")

    # Part 1: Modify FE10Data.cms (prices, attributes, ranks)
    counts = modify_fe10data()

    # Part 2: Rebuild shop files with every item
    rebuild_shops()

    # Part 3: Update FST with new shop file sizes
    update_fst()

    # --- Final summary ---
    safe_print("=" * 60)
    safe_print("MOD APPLIED SUCCESSFULLY")
    safe_print("=" * 60)
    safe_print("")
    safe_print("Summary of changes:")
    safe_print(f"  Item prices zeroed:      {counts['prices_zeroed']}")
    safe_print(f"  Sealsteal removed:       {counts['sealsteal_removed']}")
    safe_print(f"  Valuable removed:        {counts['valuable_removed']}")
    safe_print(f"  eq* attributes removed:  {counts['eq_removed']}")
    safe_print(f"  Rank N -> D changed:     {counts['rank_changed']}")
    safe_print(f"  Shop files rebuilt:       3 (normal, hard, maniac)")
    safe_print(f"  FST entries updated:      3")
    safe_print("")
    safe_print("Modified files:")
    safe_print(f"  Game/DATA/files/FE10Data.cms")
    safe_print(f"  Game/DATA/files/FE10Data_decompressed.bin")
    safe_print(f"  Game/DATA/files/Shop/shopitem_n.bin")
    safe_print(f"  Game/DATA/files/Shop/shopitem_m.bin")
    safe_print(f"  Game/DATA/files/Shop/shopitem_h.bin")
    safe_print(f"  Game/DATA/sys/fst.bin")
    safe_print("")
    safe_print("Original files preserved in Backup/")
    safe_print("")


if __name__ == "__main__":
    main()
