"""Shop file (shopitem_*.bin) CMS binary parser.

Parses a CMS-format shop binary and returns per-chapter inventories,
SHOP_PERSON data, FSHOP forge data, and FSHOP_CARD metadata.
"""

import struct

from fe10_mod_editor.core.cms_parser import parse_cms_header, resolve_string

# All 43 chapter IDs in order
CHAPTERS = [
    "C0000", "C0101", "C0102", "C0103", "C0104", "C0105", "C0106",
    "C0107", "C0108", "C0109", "C0110", "C0111",
    "C0201", "C0202", "C0203", "C0204", "C0205",
    "C0301", "C0302", "C0303", "C0304", "C0305", "C0306", "C0307",
    "C0308", "C0309", "C0310", "C0311", "C0312", "C0313", "C0314", "C0315",
    "C0401", "C0402", "C0403", "C0404", "C0405", "C0406",
    "C0407a", "C0407b", "C0407c", "C0407d", "C0407e",
]

# 4 tutorial IDs
TUTORIALS = ["T01", "T02", "T03", "T04"]

DATA_START = 0x20


def parse_shop_file(path: str) -> dict:
    """Parse a CMS shop binary file and return all section data.

    Args:
        path: Filesystem path to a shopitem_*.bin file.

    Returns:
        Dictionary with keys:
            chapters        - list of 43 chapter IDs
            tutorials       - list of 4 tutorial IDs
            shop_person_data - {chapter_or_tutorial: 4 raw bytes}
            wshop_items     - {chapter: [IID_string, ...]}
            ishop_items     - {chapter: [IID_string, ...]}
            fshop_data      - {chapter: [(raw_value, resolved_string_or_None), ...] (180 dwords)}
            fshop_card_entries - [(mess_string, 8_raw_bytes), ...]
    """
    with open(path, "rb") as f:
        data = f.read()

    header = parse_cms_header(data)
    data_region_size = header["data_region_size"]
    ptr1_count = header["ptr1_count"]
    ptr2_count = header["ptr2_count"]

    ptr1_start = DATA_START + data_region_size
    ptr2_start = ptr1_start + ptr1_count * 4
    label_start = ptr2_start + ptr2_count * 8

    # Build pointer table 1 set (data-relative offsets that hold string pointers)
    pt1_set = set()
    for i in range(ptr1_count):
        off = ptr1_start + i * 4
        val = struct.unpack(">I", data[off:off + 4])[0]
        pt1_set.add(val)

    # Parse the subsection table (pointer table 2) to get labelled sections
    sub_entries = []
    for i in range(ptr2_count):
        off = ptr2_start + i * 8
        data_off, label_off = struct.unpack(">II", data[off:off + 8])
        lbl_abs = label_start + label_off
        lbl_end = data.index(b"\x00", lbl_abs)
        label = data[lbl_abs:lbl_end].decode("ascii")
        sub_entries.append((label, data_off))

    sub_dict = {label: data_off for label, data_off in sub_entries}

    # ---- SHOP_PERSON: 4 raw bytes per chapter/tutorial (NOT pointers) ----
    shop_person_data = {}
    for ch in CHAPTERS + TUTORIALS:
        label = "SHOP_PERSON_" + ch
        doff = sub_dict[label]
        abs_off = DATA_START + doff
        shop_person_data[ch] = data[abs_off:abs_off + 4]

    # ---- Sort WSHOP / ISHOP / FSHOP subsections by data offset ----
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

    # ---- WSHOP: per-chapter weapon IID lists ----
    # Each entry is 8 bytes: IID pointer (4) + 4 zero bytes, terminated by null dword
    wshop_items = {}
    for i, (label, off) in enumerate(wshop_sorted):
        ch = label.replace("WSHOP_ITEMS_", "")
        if i + 1 < len(wshop_sorted):
            next_off = wshop_sorted[i + 1][1]
        else:
            next_off = ishop_sorted[0][1]

        total_bytes = next_off - off
        items = []
        j = 0
        # Walk pairs of dwords; last dword is the null terminator
        while j < total_bytes - 4:
            ptr_val = struct.unpack(">I", data[DATA_START + off + j:DATA_START + off + j + 4])[0]
            if ptr_val != 0:
                s = resolve_string(data, ptr_val)
                if s is not None:
                    items.append(s)
            j += 8  # skip IID ptr (4) + zero padding (4)
        wshop_items[ch] = items

    # ---- ISHOP: per-chapter item IID lists ----
    # Same format as WSHOP, with optional bargain flags in 2nd dword
    ishop_items = {}
    for i, (label, off) in enumerate(ishop_sorted):
        ch = label.replace("ISHOP_ITEMS_", "")
        if i + 1 < len(ishop_sorted):
            next_off = ishop_sorted[i + 1][1]
        else:
            next_off = fshop_sorted[0][1]

        total_bytes = next_off - off
        items = []
        if total_bytes > 4:
            j = 0
            while j < total_bytes - 4:
                ptr_val = struct.unpack(">I", data[DATA_START + off + j:DATA_START + off + j + 4])[0]
                if ptr_val != 0:
                    s = resolve_string(data, ptr_val)
                    if s is not None:
                        items.append(s)
                j += 8
        ishop_items[ch] = items

    # ---- FSHOP: 43 chapters, each 180 dwords (720 bytes) ----
    # 60 triplets of MIK/MDV/IID — string pointers identified via PT1 set
    fshop_data = {}
    for label, off in fshop_sorted:
        ch = label.replace("FSHOP_ITEMS_", "")
        abs_off = DATA_START + off
        dwords = []
        for d in range(180):
            val = struct.unpack(">I", data[abs_off + d * 4:abs_off + d * 4 + 4])[0]
            doff = off + d * 4
            if val == 0:
                dwords.append((0, None))
            elif doff in pt1_set:
                s = resolve_string(data, val)
                dwords.append((val, s))
            else:
                dwords.append((val, None))
        fshop_data[ch] = dwords

    # ---- FSHOP_CARD: count(4 bytes) + entries of (MESS_ptr(4) + raw(8)) ----
    fshop_card_off = sub_dict["FSHOP_CARD_DATA"]
    fshop_card_abs = DATA_START + fshop_card_off
    card_count = data[fshop_card_abs + 3]  # count stored as byte at offset +3

    fshop_card_entries = []
    for i in range(card_count):
        entry_start = fshop_card_abs + 4 + i * 12
        mess_ptr = struct.unpack(">I", data[entry_start:entry_start + 4])[0]
        mess_str = resolve_string(data, mess_ptr)
        raw_bytes = data[entry_start + 4:entry_start + 12]
        fshop_card_entries.append((mess_str, raw_bytes))

    return {
        "chapters": list(CHAPTERS),
        "tutorials": list(TUTORIALS),
        "shop_person_data": shop_person_data,
        "wshop_items": wshop_items,
        "ishop_items": ishop_items,
        "fshop_data": fshop_data,
        "fshop_card_entries": fshop_card_entries,
    }
