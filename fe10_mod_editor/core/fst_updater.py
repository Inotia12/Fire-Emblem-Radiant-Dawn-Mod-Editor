"""Patch the File System Table (fst.bin) with updated file sizes.

FST entries are 12 bytes each:
  - Bytes 0-3: name offset
  - Bytes 4-7: file offset on disc
  - Bytes 8-11: file size (big-endian u32)
"""

import struct

FST_SHOP_INDICES = {
    "shopitem_h.bin": 1788,
    "shopitem_m.bin": 1789,
    "shopitem_n.bin": 1790,
}


def patch_fst_sizes(fst_data: bytes, size_map: dict[str, int]) -> bytes:
    """Patch file size entries in FST data.

    Args:
        fst_data: Original fst.bin contents.
        size_map: Dict of filename -> new file size.

    Returns:
        Patched FST data as bytes.
    """
    result = bytearray(fst_data)

    for fname, new_size in size_map.items():
        if fname not in FST_SHOP_INDICES:
            raise ValueError(f"Unknown FST entry: {fname}")
        entry_index = FST_SHOP_INDICES[fname]
        size_offset = entry_index * 12 + 8
        struct.pack_into(">I", result, size_offset, new_size)

    return bytes(result)
