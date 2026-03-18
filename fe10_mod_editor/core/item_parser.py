"""Parse the ItemData section from decompressed FE10Data binary.

Item entries start at offset 0xDF44. The first 4 bytes are the item count (u32 BE).
Each item has a 56-byte fixed header followed by variable-length trailing data
(attribute pointers, effectiveness pointers, PRF data).
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

ITEM_DATA_OFFSET = 0xDF44


def parse_all_items(data: bytes) -> list[dict]:
    """Parse all item entries from decompressed FE10Data.

    Args:
        data: Full decompressed FE10Data binary.

    Returns:
        List of dicts, one per item. Each dict contains all parsed fields.
        The 'byte_offset' field records where the entry starts in the data
        (needed for applying edits back to binary).
    """
    item_count = struct.unpack(">I", data[ITEM_DATA_OFFSET:ITEM_DATA_OFFSET + 4])[0]
    pos = ITEM_DATA_OFFSET + 4
    items = []

    for _ in range(item_count):
        entry_start = pos

        # Fixed header fields
        iid_ptr = struct.unpack(">I", data[pos:pos + 4])[0]
        miid_ptr = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        help_ptr = struct.unpack(">I", data[pos + 8:pos + 12])[0]
        disp_type_ptr = struct.unpack(">I", data[pos + 12:pos + 16])[0]
        actual_type_ptr = struct.unpack(">I", data[pos + 16:pos + 20])[0]
        rank_ptr = struct.unpack(">I", data[pos + 20:pos + 24])[0]

        icon_id = data[pos + 37]
        price = struct.unpack(">H", data[pos + 38:pos + 40])[0]
        might = data[pos + 40]
        accuracy = data[pos + 41]
        critical = data[pos + 42]
        weight = data[pos + 43]
        uses = data[pos + 44]
        wexp_gain = data[pos + 45]
        min_range = data[pos + 46]
        max_range = data[pos + 47]

        attr_count = data[pos + 53]
        eff_count = data[pos + 54]
        prf_flag = data[pos + 55]

        # Variable trailing data: attributes
        attributes = []
        for a in range(attr_count):
            attr_off = pos + 56 + a * 4
            attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
            attr_str = resolve_string(data, attr_ptr)
            if attr_str:
                attributes.append(attr_str)

        # Advance past the full entry
        entry_size = 56 + (attr_count * 4) + (eff_count * 4) + (prf_flag * 12)
        pos += entry_size

        items.append({
            "iid": resolve_string(data, iid_ptr) or "",
            "miid": resolve_string(data, miid_ptr) or "",
            "help_text": resolve_string(data, help_ptr) or "",
            "display_type": resolve_string(data, disp_type_ptr) or "",
            "weapon_type": resolve_string(data, actual_type_ptr) or "",
            "weapon_rank": resolve_string(data, rank_ptr) or "",
            "icon_id": icon_id,
            "price": price,
            "might": might,
            "accuracy": accuracy,
            "critical": critical,
            "weight": weight,
            "uses": uses,
            "wexp_gain": wexp_gain,
            "min_range": min_range,
            "max_range": max_range,
            "attributes": attributes,
            "effectiveness_count": eff_count,
            "prf_flag": prf_flag,
            "byte_offset": entry_start,
            # Store raw pointer values needed for binary editing
            "_rank_ptr": rank_ptr,
            "_iid_ptr": iid_ptr,
        })

    return items
