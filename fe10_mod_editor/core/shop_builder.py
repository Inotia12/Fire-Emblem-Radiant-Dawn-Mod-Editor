"""Shop file builder (CompressShopfile algorithm).

Constructs a complete CMS shop binary (shopitem_*.bin) from scratch,
given parsed section data and per-chapter item lists.

The algorithm faithfully mirrors the C# randomizer's CompressShopfile
method: write data sections, string pool, pointer tables, subsection
table, label strings, then back-fill pointers and the CMS header.
"""

import struct

from fe10_mod_editor.core.shop_parser import CHAPTERS, TUTORIALS


def build_shop_file(
    orig_info: dict,
    wshop_items: list[str] | dict[str, list[str]],
    ishop_items: list[str] | dict[str, list[str]],
) -> bytes:
    """Build a complete CMS shop binary from section data and item lists.

    Args:
        orig_info: Dict returned by ``parse_shop_file`` containing at least:
            shop_person_data, fshop_data, fshop_card_entries.
        wshop_items: Either a flat list of IID strings (applied to all 43
            chapters) or a dict mapping chapter ID -> list of IID strings.
        ishop_items: Same format as *wshop_items* but for consumable items.

    Returns:
        The complete CMS binary as ``bytes``, ready to write to disk.
    """
    chapters = CHAPTERS
    tutorials = TUTORIALS
    shop_person_data = orig_info["shop_person_data"]
    fshop_data = orig_info["fshop_data"]
    fshop_card_entries = orig_info["fshop_card_entries"]

    # Normalise flat lists into per-chapter dicts
    if isinstance(wshop_items, list):
        _wshop_flat = wshop_items
        wshop_items = {ch: list(_wshop_flat) for ch in chapters}
    if isinstance(ishop_items, list):
        _ishop_flat = ishop_items
        ishop_items = {ch: list(_ishop_flat) for ch in chapters}

    # --- Tracking lists (matching randomizer's approach) ---
    labels: list[str] = []        # subsection labels in data-write order
    dataoffsets: list[int] = []   # file offset where each subsection's data starts
    pointernames: list[str] = []  # string name for each pointer (in write order)
    pointerloc: list[int] = []    # file offset of each pointer slot (in write order)

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

    # --- WSHOP sections (43 chapters) - per-chapter weapon items ---
    for ch in chapters:
        labels.append("WSHOP_ITEMS_" + ch)
        dataoffsets.append(len(out))
        for iid in wshop_items[ch]:
            pointernames.append(iid)
            pointerloc.append(len(out))
            out.extend(bytes(4))
            out.extend(bytes(4))
        out.extend(bytes(4))

    # --- ISHOP sections (43 chapters) - per-chapter consumable items ---
    for ch in chapters:
        labels.append("ISHOP_ITEMS_" + ch)
        dataoffsets.append(len(out))
        for iid in ishop_items[ch]:
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
                # Non-zero, non-pointer value
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
    string_offsets: dict[str, int] = {}  # string -> file offset in output

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
    # Written in insertion order (naturally ascending since we write sequentially)
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
    label_string_offsets: dict[str, int] = {}
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
