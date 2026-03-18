"""CMS binary format parsing utilities.

CMS files use a pointer convention where all stored pointer values equal
the actual file offset minus 0x20. To resolve a pointer: add 0x20 to get
the real offset in the file.
"""

import struct


def resolve_string(data: bytes, ptr: int) -> str | None:
    """Resolve a CMS string pointer to a Python string.

    Args:
        data: The full file/decompressed data buffer.
        ptr: The stored pointer value (actual_file_offset - 0x20).

    Returns:
        The decoded ASCII string, or None if pointer is null/empty/out-of-bounds.
    """
    if ptr == 0:
        return None
    offset = ptr + 0x20
    if offset >= len(data) or data[offset] == 0:
        return None
    end = data.index(0, offset)
    return data[offset:end].decode("ascii", errors="replace")


def parse_cms_header(data: bytes) -> dict:
    """Parse the 40-byte CMS file header.

    Returns dict with keys: file_size, data_region_size, ptr1_count, ptr2_count.
    """
    file_size, data_region_size, ptr1_count, ptr2_count = struct.unpack(">IIII", data[0:16])
    return {
        "file_size": file_size,
        "data_region_size": data_region_size,
        "ptr1_count": ptr1_count,
        "ptr2_count": ptr2_count,
    }
