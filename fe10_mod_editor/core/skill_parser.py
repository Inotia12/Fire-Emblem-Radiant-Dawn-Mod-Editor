"""Parse the SkillData section from decompressed FE10Data binary.

SkillData entries start at offset 0x12810. The first 4 bytes are the entry
count (u32 BE). Each entry is fixed-size: 0x2C (44) bytes.

Entry structure (offsets relative to entry start):
  0-3:    SID string pointer (skill ID)
  4-7:    MSID string pointer (display name)
  8-11:   Help text pointer
  12-15:  Help text 2 pointer
  16-19:  Unknown pointer
  20-23:  Effect pointer
  24-27:  Item pointer
  28:     Counter value (i8)
  29:     Visibility (1=visible, 2=grayed, 3=hidden)
  30:     Capacity cost (i8)
  31:     Unknown byte
  32:     Restriction table 1 count
  33:     Restriction table 2 count
  34-35:  Padding (2 bytes)
  36-39:  Restriction table 1 pointer
  40-43:  Restriction table 2 pointer

Note: The spec states restriction pointers are at offsets 34 and 38, but the
actual binary has 2 padding bytes after the counts, putting pointers at
offsets 36 and 40.

Restriction table entries are 8 bytes each: flag byte + 3 null bytes + 4-byte
ID string pointer.
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

SKILL_DATA_OFFSET = 0x12810
SKILL_ENTRY_SIZE = 0x2C  # 44 bytes


def _parse_restriction_table(data: bytes, ptr: int, count: int) -> list[str]:
    """Parse a restriction table and return a list of ID strings.

    Each table entry is 8 bytes: flag (u8) + 3 null bytes + 4-byte pointer.

    Args:
        data: Full decompressed FE10Data binary.
        ptr: CMS pointer to the start of the restriction table.
        count: Number of entries in the table.

    Returns:
        List of resolved ID strings (skipping None values).
    """
    if count == 0 or ptr == 0:
        return []

    actual_offset = ptr + 0x20
    results = []
    for i in range(count):
        entry_off = actual_offset + i * 8
        # flag = data[entry_off]  # Not needed for ID list
        id_ptr = struct.unpack(">I", data[entry_off + 4:entry_off + 8])[0]
        id_str = resolve_string(data, id_ptr)
        if id_str:
            results.append(id_str)
    return results


def parse_all_skills(data: bytes) -> list[dict]:
    """Parse all skill entries from decompressed FE10Data.

    Args:
        data: Full decompressed FE10Data binary.

    Returns:
        List of dicts, one per skill. Each dict contains all parsed fields.
        The 'byte_offset' field records where the entry starts in the data.
    """
    count = struct.unpack(">I", data[SKILL_DATA_OFFSET:SKILL_DATA_OFFSET + 4])[0]
    pos = SKILL_DATA_OFFSET + 4
    skills = []

    for _ in range(count):
        entry_start = pos

        sid_ptr = struct.unpack(">I", data[pos:pos + 4])[0]
        msid_ptr = struct.unpack(">I", data[pos + 4:pos + 8])[0]

        counter = struct.unpack("b", bytes([data[pos + 28]]))[0]
        visibility = data[pos + 29]
        capacity_cost = struct.unpack("b", bytes([data[pos + 30]]))[0]
        unknown = data[pos + 31]

        restrict1_count = data[pos + 32]
        restrict2_count = data[pos + 33]
        # Bytes 34-35 are padding
        restrict1_ptr = struct.unpack(">I", data[pos + 36:pos + 40])[0]
        restrict2_ptr = struct.unpack(">I", data[pos + 40:pos + 44])[0]

        whitelist = _parse_restriction_table(data, restrict1_ptr, restrict1_count)
        blacklist = _parse_restriction_table(data, restrict2_ptr, restrict2_count)

        pos += SKILL_ENTRY_SIZE

        skills.append({
            "sid": resolve_string(data, sid_ptr) or "",
            "msid": resolve_string(data, msid_ptr) or "",
            "counter": counter,
            "visibility": visibility,
            "capacity_cost": capacity_cost,
            "unknown": unknown,
            "whitelist": whitelist,
            "blacklist": blacklist,
            "byte_offset": entry_start,
        })

    return skills
