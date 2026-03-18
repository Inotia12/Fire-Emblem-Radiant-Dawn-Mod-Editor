"""
Rebuild Fire Emblem: Radiant Dawn shop files (shopitem_n/m/h.bin)
using the EXACT same algorithm as the fe10-randomizer CompressShopfile.

Algorithm (matching the C# randomizer):
1. Write 40 zero bytes as placeholder header (0x28 bytes)
2. Write data sections in order: SHOP_PERSON, WSHOP, ISHOP, FSHOP, FSHOP_CARD
3. Write string pool (sorted, deduplicated, null-terminated, 4-byte aligned)
4. Write Pointer Table 1 (data offsets where string pointers live, in insertion order)
5. Write Pointer Table 2 (subsection table: data_offset + label_string_offset, sorted by label)
6. Write label strings
7. Back-fill all string pointer values in the data region
8. Write final header
"""

import struct
import glob
import os

# ============================================================================
# Resolve base directory using glob to handle the colon in the path
# ============================================================================
BASE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Game", "DATA", "files")
if not os.path.isdir(BASE):
    raise FileNotFoundError(f"Cannot find {BASE}")
SHOP_DIR = os.path.join(BASE, "Shop")
FE10DATA_PATH = os.path.join(BASE, "FE10Data_decompressed.bin")


def resolve_string(data, ptr):
    """Resolve a big-endian pointer to an ASCII string in the data region."""
    if ptr == 0:
        return None
    offset = ptr + 0x20
    if offset >= len(data) or data[offset] == 0:
        return None
    end = data.index(0, offset)
    return data[offset:end].decode("ascii", errors="replace")


def int2bytes_be(val):
    """Convert int to 4 big-endian bytes (matching randomizer's int2bytes)."""
    return struct.pack(">I", val)


# ============================================================================
# Parse FE10Data to get all items and categorize them
# ============================================================================
def parse_items():
    with open(FE10DATA_PATH, "rb") as f:
        fe = f.read()

    item_count = struct.unpack(">I", fe[0xDF44:0xDF48])[0]
    pos = 0xDF48

    exclude_prefixes = [
        "IID_JOG_", "IID_JUDGE", "IID_SPRT_HEAL",
        "IID_DHEGINHANSEA", "IID_LEKAIN", "IID_CEPHERAN",
    ]
    weapon_types = {
        "sword", "lance", "axe", "bow", "knife",
        "flame", "thunder", "wind", "light", "dark",
        "card", "ballista",
    }

    wshop_items = []
    ishop_items = []

    for _ in range(item_count):
        iid_ptr = struct.unpack(">I", fe[pos:pos + 4])[0]
        iid = resolve_string(fe, iid_ptr) or ""
        disp_ptr = struct.unpack(">I", fe[pos + 12:pos + 16])[0]
        disp = resolve_string(fe, disp_ptr) or ""
        ac = fe[pos + 53]
        ec = fe[pos + 54]
        pf = fe[pos + 55]
        entry_size = 56 + ac * 4 + ec * 4 + pf * 12

        attrs = []
        for a in range(ac):
            ap = struct.unpack(">I", fe[pos + 56 + a * 4:pos + 60 + a * 4])[0]
            attrs.append(resolve_string(fe, ap) or "")

        pos += entry_size

        # Exclusion filters
        if "blow" in attrs:
            continue
        if any(iid.startswith(p) for p in exclude_prefixes):
            continue
        if "longfar" in attrs and "sh" in attrs:
            continue
        if "stone" in attrs:
            continue

        if disp in weapon_types:
            wshop_items.append(iid)
        else:
            ishop_items.append(iid)

    return wshop_items, ishop_items


# ============================================================================
# Parse the original .bak file to extract structure and data
# ============================================================================
def parse_original(bak_path):
    with open(bak_path, "rb") as f:
        orig = f.read()

    h = struct.unpack(">IIII", orig[0:16])
    file_size = h[0]
    data_region_size = h[1]
    ptr1_count = h[2]
    ptr2_count = h[3]

    data_start = 0x20
    ptr1_start = data_start + data_region_size
    ptr2_start = ptr1_start + ptr1_count * 4
    label_start = ptr2_start + ptr2_count * 8

    # Build pointer table 1 set (for identifying which data offsets are pointers)
    pt1_set = set()
    for i in range(ptr1_count):
        off = ptr1_start + i * 4
        val = struct.unpack(">I", orig[off:off + 4])[0]
        pt1_set.add(val)

    # Parse subsection table
    sub_entries = []
    for i in range(ptr2_count):
        off = ptr2_start + i * 8
        data_off, label_off = struct.unpack(">II", orig[off:off + 8])
        lbl_abs = label_start + label_off
        lbl_end = orig.index(b"\x00", lbl_abs)
        label = orig[lbl_abs:lbl_end].decode("ascii")
        sub_entries.append((label, data_off))

    sub_dict = {label: data_off for label, data_off in sub_entries}

    # ---- SHOP_PERSON: 47 entries of 4 bytes each, raw data (NOT pointers) ----
    # Chapters + tutorials
    chapters = [
        "C0000", "C0101", "C0102", "C0103", "C0104", "C0105", "C0106",
        "C0107", "C0108", "C0109", "C0110", "C0111",
        "C0201", "C0202", "C0203", "C0204", "C0205",
        "C0301", "C0302", "C0303", "C0304", "C0305", "C0306", "C0307",
        "C0308", "C0309", "C0310", "C0311", "C0312", "C0313", "C0314", "C0315",
        "C0401", "C0402", "C0403", "C0404", "C0405", "C0406",
        "C0407a", "C0407b", "C0407c", "C0407d", "C0407e",
    ]
    tutorials = ["T01", "T02", "T03", "T04"]

    shop_person_data = {}
    for ch in chapters + tutorials:
        label = "SHOP_PERSON_" + ch
        doff = sub_dict[label]
        abs_off = data_start + doff
        shop_person_data[ch] = orig[abs_off:abs_off + 4]

    # ---- WSHOP: items per chapter ----
    wshop_sorted = sorted(
        [(l, o) for l, o in sub_entries if l.startswith("WSHOP_ITEMS_")],
        key=lambda x: x[1],
    )
    ishop_sorted = sorted(
        [(l, o) for l, o in sub_entries if l.startswith("ISHOP_ITEMS_")],
        key=lambda x: x[1],
    )
    fshop_sorted = sorted(
        [(l, o) for l, o in sub_entries if l.startswith("FSHOP_ITEMS_")],
        key=lambda x: x[1],
    )

    wshop_counts = {}
    for i, (label, off) in enumerate(wshop_sorted):
        ch = label.replace("WSHOP_ITEMS_", "")
        if i + 1 < len(wshop_sorted):
            next_off = wshop_sorted[i + 1][1]
        else:
            next_off = ishop_sorted[0][1]
        total_dwords = (next_off - off) // 4
        # Count actual items (non-null IID pointers in pairs)
        real_items = 0
        for j in range(0, total_dwords - 1, 2):
            val = struct.unpack(">I", orig[data_start + off + j * 4:data_start + off + j * 4 + 4])[0]
            if val != 0:
                real_items += 1
        wshop_counts[ch] = real_items

    ishop_counts = {}
    for i, (label, off) in enumerate(ishop_sorted):
        ch = label.replace("ISHOP_ITEMS_", "")
        if i + 1 < len(ishop_sorted):
            next_off = ishop_sorted[i + 1][1]
        else:
            next_off = fshop_sorted[0][1]
        total_bytes = next_off - off
        if total_bytes == 4:
            ishop_counts[ch] = 0
        else:
            real_items = 0
            j = 0
            while j < total_bytes - 4:
                val = struct.unpack(">I", orig[data_start + off + j:data_start + off + j + 4])[0]
                if val != 0:
                    real_items += 1
                j += 8
            ishop_counts[ch] = real_items

    # ---- FSHOP: 43 chapters, each 720 bytes (180 dwords = 60 triplets of MIK/MDV/IID) ----
    fshop_data = {}
    for label, off in fshop_sorted:
        ch = label.replace("FSHOP_ITEMS_", "")
        abs_off = data_start + off
        # Read 180 dwords, resolve string pointers
        dwords = []
        for d in range(180):
            val = struct.unpack(">I", orig[abs_off + d * 4:abs_off + d * 4 + 4])[0]
            doff = off + d * 4
            if val == 0:
                dwords.append((0, None))
            elif doff in pt1_set:
                s = resolve_string(orig, val)
                dwords.append((val, s))
            else:
                dwords.append((val, None))
        fshop_data[ch] = dwords

    # ---- FSHOP_CARD: count(4 bytes) + entries of (MESS_ptr(4) + raw(8)) ----
    fshop_card_off = sub_dict["FSHOP_CARD_DATA"]
    fshop_card_abs = data_start + fshop_card_off
    card_count = orig[fshop_card_abs + 3]  # count stored as byte at offset +3

    fshop_card_entries = []
    for i in range(card_count):
        entry_start = fshop_card_abs + 4 + i * 12
        mess_ptr = struct.unpack(">I", orig[entry_start:entry_start + 4])[0]
        mess_str = resolve_string(orig, mess_ptr)
        raw_bytes = orig[entry_start + 4:entry_start + 12]
        fshop_card_entries.append((mess_str, raw_bytes))

    return {
        "chapters": chapters,
        "tutorials": tutorials,
        "shop_person_data": shop_person_data,
        "wshop_counts": wshop_counts,
        "ishop_counts": ishop_counts,
        "fshop_data": fshop_data,
        "fshop_card_entries": fshop_card_entries,
    }


# ============================================================================
# Build the shop file using the randomizer's CompressShopfile algorithm
# ============================================================================
def build_shop_file(orig_info, wshop_items, ishop_items):
    chapters = orig_info["chapters"]
    tutorials = orig_info["tutorials"]
    shop_person_data = orig_info["shop_person_data"]
    wshop_counts = orig_info["wshop_counts"]
    ishop_counts = orig_info["ishop_counts"]
    fshop_data = orig_info["fshop_data"]
    fshop_card_entries = orig_info["fshop_card_entries"]

    # --- Tracking lists (matching randomizer's approach) ---
    labels = []           # subsection labels in data-write order
    dataoffsets = []       # file offset where each subsection's data starts
    pointernames = []      # string name for each pointer (in write order)
    pointerloc = []        # file offset of each pointer slot (in write order)

    # --- Build output buffer ---
    out = bytearray()

    # Step 1: Write 40 zero bytes as placeholder header (0x28 = 40)
    out.extend(b"\x00" * 40)

    # Step 2: Write data sections in order

    # --- SHOP_PERSON sections (47 entries: 43 chapters + 4 tutorials) ---
    for ch in chapters:
        labels.append("SHOP_PERSON_" + ch)
        dataoffsets.append(len(out))
        out.extend(shop_person_data[ch])  # 4 raw bytes, NOT pointers

    for t in tutorials:
        labels.append("SHOP_PERSON_" + t)
        dataoffsets.append(len(out))
        out.extend(shop_person_data[t])  # 4 raw bytes

    # --- WSHOP sections (43 chapters) - ALL items for ALL chapters ---
    for ch in chapters:
        labels.append("WSHOP_ITEMS_" + ch)
        dataoffsets.append(len(out))
        for iid in wshop_items:
            pointernames.append(iid)
            pointerloc.append(len(out))
            out.extend(bytes(4))
            out.extend(bytes(4))
        out.extend(bytes(4))

    # --- ISHOP sections (43 chapters) - ALL items for ALL chapters ---
    for ch in chapters:
        labels.append("ISHOP_ITEMS_" + ch)
        dataoffsets.append(len(out))
        for iid in ishop_items:
            pointernames.append(iid)
            pointerloc.append(len(out))
            out.extend(bytes(4))
            out.extend(bytes(4))
        out.extend(bytes(4))

    # --- FSHOP sections (43 chapters, each 180 dwords = 720 bytes) ---
    for ch in chapters:
        labels.append("FSHOP_ITEMS_" + ch)
        dataoffsets.append(len(out))
        dwords = fshop_data[ch]
        for val, string in dwords:
            if val == 0:
                out.extend(b"\x00\x00\x00\x00")
            elif string is not None:
                # This is a string pointer - track it
                pointernames.append(string)
                pointerloc.append(len(out))
                out.extend(b"\x00\x00\x00\x00")  # placeholder
            else:
                # Non-zero, non-pointer value (shouldn't happen for FSHOP but handle it)
                out.extend(struct.pack(">I", val))

    # --- FSHOP_CARD section ---
    labels.append("FSHOP_CARD_DATA")
    dataoffsets.append(len(out))

    # Write 4 zero bytes (count will be back-filled at byte +3)
    card_section_start = len(out)
    out.extend(b"\x00\x00\x00\x00")

    card_count = len(fshop_card_entries)
    for mess_str, raw_bytes in fshop_card_entries:
        # MESS pointer (placeholder)
        pointernames.append(mess_str)
        pointerloc.append(len(out))
        out.extend(b"\x00\x00\x00\x00")
        # 8 raw bytes
        out.extend(raw_bytes)

    # Back-fill card count at byte +3 of the section
    out[card_section_start + 3] = card_count

    # Step 3: Write string pool
    # Collect all unique strings, sort alphabetically
    all_strings = sorted(set(pointernames))

    # Pad to 4-byte alignment before string pool
    while len(out) % 4 != 0:
        out.append(0)

    string_pool_start = len(out)
    string_offsets = {}  # string -> file offset in output

    for s in all_strings:
        string_offsets[s] = len(out)
        out.extend(s.encode("ascii"))
        out.append(0)

    # Pad string pool to 4-byte alignment
    while len(out) % 4 != 0:
        out.append(0)

    # Step 4: Data region size (from byte 0x20 to here)
    data_region_size = len(out) - 0x20

    # Step 5: Write Pointer Table 1
    # Entries are file offsets (- 0x20) where string pointers live
    # Written in insertion order (which is naturally ascending since we write sequentially)
    ptr_table_1_start = len(out)
    for loc in pointerloc:
        out.extend(struct.pack(">I", loc - 0x20))

    # Step 6: Write Pointer Table 2 (subsection table)
    # Must be sorted alphabetically by label name
    # Each entry = 8 bytes: data_offset(4, relative to 0x20) + label_string_offset(4)

    # Sort labels alphabetically, maintaining their data offsets
    label_pairs = list(zip(labels, dataoffsets))
    label_pairs_sorted = sorted(label_pairs, key=lambda x: x[0])

    # Build label string region
    label_bytes = bytearray()
    label_string_offsets = {}
    for lbl, _ in label_pairs_sorted:
        if lbl not in label_string_offsets:
            label_string_offsets[lbl] = len(label_bytes)
            label_bytes.extend(lbl.encode("ascii"))
            label_bytes.append(0)

    # Write subsection table entries
    for lbl, doff in label_pairs_sorted:
        out.extend(struct.pack(">I", doff - 0x20))  # data offset relative to 0x20
        out.extend(struct.pack(">I", label_string_offsets[lbl]))

    # Step 7: Write label strings
    out.extend(label_bytes)

    # Final file size
    file_size = len(out)

    # Step 8: Back-fill all string pointer values
    # Each pointer slot gets the string's file offset - 0x20
    for i, loc in enumerate(pointerloc):
        s = pointernames[i]
        str_file_off = string_offsets[s]
        struct.pack_into(">I", out, loc, str_file_off - 0x20)

    # Step 9: Write header
    struct.pack_into(">I", out, 0x00, file_size)
    struct.pack_into(">I", out, 0x04, data_region_size)
    struct.pack_into(">I", out, 0x08, len(pointerloc))
    struct.pack_into(">I", out, 0x0C, len(label_pairs_sorted))

    return bytes(out)


# ============================================================================
# Verification
# ============================================================================
def verify_shop_file(data, label=""):
    h = struct.unpack(">IIII", data[0:16])
    file_size = h[0]
    data_region_size = h[1]
    ptr1_count = h[2]
    ptr2_count = h[3]

    print(f"  File size: {len(data)} (header says {file_size}) {'OK' if len(data) == file_size else 'MISMATCH!'}")
    print(f"  Data region size: {data_region_size} (0x{data_region_size:X})")
    print(f"  Pointer table 1: {ptr1_count} entries")
    print(f"  Pointer table 2: {ptr2_count} entries (subsections)")

    ptr1_start = 0x20 + data_region_size
    ptr2_start = ptr1_start + ptr1_count * 4
    label_start = ptr2_start + ptr2_count * 8

    print(f"  Ptr table 1 at: 0x{ptr1_start:X}")
    print(f"  Ptr table 2 at: 0x{ptr2_start:X}")
    print(f"  Label pool at:  0x{label_start:X}")

    # Read a few subsection entries
    print(f"  First 5 subsections:")
    for i in range(min(5, ptr2_count)):
        off = ptr2_start + i * 8
        data_off, label_off = struct.unpack(">II", data[off:off + 8])
        lbl_abs = label_start + label_off
        lbl_end = data.index(b"\x00", lbl_abs)
        lbl = data[lbl_abs:lbl_end].decode("ascii")
        print(f"    {lbl} -> data_off=0x{data_off:06X}")

    # Verify a few string pointers resolve correctly
    if ptr1_count > 2:
        print(f"  First 3 pointer resolutions:")
        for i in range(min(3, ptr1_count)):
            ptr_off = ptr1_start + i * 4
            data_off = struct.unpack(">I", data[ptr_off:ptr_off + 4])[0]
            ptr_val = struct.unpack(">I", data[0x20 + data_off:0x20 + data_off + 4])[0]
            str_abs = 0x20 + ptr_val
            if str_abs < len(data):
                end = data.index(b"\x00", str_abs)
                s = data[str_abs:end].decode("ascii", errors="replace")
                print(f"    PT1[{i}]: data_off=0x{data_off:06X} -> string_off=0x{ptr_val:06X} -> \"{s}\"")


# ============================================================================
# Main
# ============================================================================
def main():
    print("=" * 70)
    print("Rebuilding shop files (randomizer-style algorithm)")
    print("=" * 70)

    # Parse items from FE10Data
    print("\nParsing FE10Data for item lists...")
    wshop_items, ishop_items = parse_items()
    print(f"  WSHOP items: {len(wshop_items)}")
    print(f"  ISHOP items: {len(ishop_items)}")

    # Process each difficulty
    for suffix in ["n", "m", "h"]:
        bak_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "Backup", f"shopitem_{suffix}.bin")
        out_path = os.path.join(SHOP_DIR, f"shopitem_{suffix}.bin")

        print(f"\n{'=' * 70}")
        print(f"Processing shopitem_{suffix}.bin")
        print(f"{'=' * 70}")

        print(f"  Reading original: shopitem_{suffix}.bin.bak")
        orig_info = parse_original(bak_path)

        print(f"  Chapters: {len(orig_info['chapters'])}")
        print(f"  Tutorials: {len(orig_info['tutorials'])}")

        # Show item counts
        wshop_nonempty = sum(1 for c in orig_info["wshop_counts"].values() if c > 0)
        ishop_nonempty = sum(1 for c in orig_info["ishop_counts"].values() if c > 0)
        print(f"  WSHOP: {wshop_nonempty} non-empty chapters")
        print(f"  ISHOP: {ishop_nonempty} non-empty chapters")

        print(f"  Building output file...")
        output = build_shop_file(orig_info, wshop_items, ishop_items)

        print(f"  Writing: shopitem_{suffix}.bin")
        with open(out_path, "wb") as f:
            f.write(output)

        print(f"\n  Verification for shopitem_{suffix}.bin:")
        verify_shop_file(output, suffix)

    print(f"\n{'=' * 70}")
    print("Done! All three shop files rebuilt successfully.")
    print(f"{'=' * 70}")


if __name__ == "__main__":
    main()
