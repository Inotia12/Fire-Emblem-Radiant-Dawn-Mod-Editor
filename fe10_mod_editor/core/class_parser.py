"""Parse the JobData (class) section from decompressed FE10Data binary.

JobData entries start at offset 0x926C. The first 4 bytes are the entry count
(u32 BE). Each entry is variable-length: 96 + (M * 4) + (S * 4) bytes, where
M = skill_count and S = attribute/SFXC count.

Note: The spec states 92 + M*4 + S*4, but the actual binary has 4 extra bytes
(a null pointer field between the satori sign pointer and the attribute
pointers), making the true size 96 + M*4 + S*4.

Entry structure (offsets relative to entry start):
  0-3:    JID string pointer (class ID)
  4-7:    MJID string pointer (display name)
  8-11:   Japanese name pointer
  12-15:  Help text pointer
  16-19:  Promotes-from pointer
  20-23:  Promotes-to pointer
  24-27:  Alt job pointer
  28-31:  Attack item pointer
  32-35:  Animation pointer
  36-39:  Base weapon ranks pointer
  40-43:  Max weapon ranks pointer
  44:     Constitution
  45:     Armor type
  46:     Weight
  47:     Mount type
  48:     Mount weight
  49:     Skill count (M)
  50:     Attribute/SFXC count (S)
  51:     Promote level
  52:     Movement type
  53:     Default movement
  54:     Skill capacity
  55:     Vision range
  56..56+M*4-1:       Skill ID pointers
  56+M*4..59+M*4:     Satori Sign skill pointer
  60+M*4..63+M*4:     Unknown/null pointer (padding)
  64+M*4..64+M*4+S*4-1: Attribute pointers
  64+M*4+S*4..+7:     Max stats (HP, Str, Mag, Skl, Spd, Lck, Def, Res)
  +8..+15:            Base stats (signed)
  +16..+23:           Class growth rates
  +24..+31:           Promotion stat adjustments (signed)
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

JOB_DATA_OFFSET = 0x926C

STAT_NAMES = ("hp", "str", "mag", "skl", "spd", "lck", "def", "res")


def parse_all_classes(data: bytes) -> list[dict]:
    """Parse all class entries from decompressed FE10Data.

    Args:
        data: Full decompressed FE10Data binary.

    Returns:
        List of dicts, one per class. Each dict contains all parsed fields.
        The 'byte_offset' field records where the entry starts in the data.
    """
    count = struct.unpack(">I", data[JOB_DATA_OFFSET:JOB_DATA_OFFSET + 4])[0]
    pos = JOB_DATA_OFFSET + 4
    classes = []

    for _ in range(count):
        entry_start = pos

        # Fixed pointer fields (11 pointers, 44 bytes)
        jid_ptr = struct.unpack(">I", data[pos:pos + 4])[0]
        mjid_ptr = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        # Pointers at offsets 8-35 are other pointers (Japanese name, help,
        # promotes-from/to, alt job, attack item, anim)
        base_wpn_ranks_ptr = struct.unpack(">I", data[pos + 36:pos + 40])[0]
        max_wpn_ranks_ptr = struct.unpack(">I", data[pos + 40:pos + 44])[0]

        # Scalar fields (offsets 44-55)
        constitution = data[pos + 44]
        armor_type = data[pos + 45]
        weight = data[pos + 46]
        mount_type = data[pos + 47]
        mount_weight = data[pos + 48]
        skill_count = data[pos + 49]  # M
        attr_count = data[pos + 50]   # S
        promote_level = data[pos + 51]
        movement_type = data[pos + 52]
        default_movement = data[pos + 53]
        skill_capacity = data[pos + 54]
        vision_range = data[pos + 55]

        M = skill_count
        S = attr_count

        # Skill pointers (M * 4 bytes starting at offset 56)
        skill_ids = []
        for s in range(M):
            slot_off = pos + 56 + s * 4
            sid_ptr = struct.unpack(">I", data[slot_off:slot_off + 4])[0]
            skill_ids.append(resolve_string(data, sid_ptr))

        # Satori Sign skill pointer (at offset 56 + M*4)
        satori_off = pos + 56 + M * 4
        satori_ptr = struct.unpack(">I", data[satori_off:satori_off + 4])[0]
        satori_skill = resolve_string(data, satori_ptr)

        # Skip unknown/null pointer at offset 60 + M*4 (4 bytes)

        # Attribute pointers (S * 4 bytes starting at offset 64 + M*4)
        attributes = []
        for a in range(S):
            attr_off = pos + 64 + M * 4 + a * 4
            attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
            attributes.append(resolve_string(data, attr_ptr))

        # Stats region starts at offset 64 + M*4 + S*4
        stats_base = pos + 64 + M * 4 + S * 4

        # Max stats (8 unsigned bytes)
        max_stats = {}
        for i, name in enumerate(STAT_NAMES):
            max_stats[name] = data[stats_base + i]

        max_stats_offset = stats_base

        # Base stats (8 signed bytes)
        base_stats = {}
        for i, name in enumerate(STAT_NAMES):
            base_stats[name] = struct.unpack("b", bytes([data[stats_base + 8 + i]]))[0]

        # Class growth rates (8 unsigned bytes)
        class_growth_rates = {}
        for i, name in enumerate(STAT_NAMES):
            class_growth_rates[name] = data[stats_base + 16 + i]

        # Promotion stat adjustments (8 signed bytes)
        promotion_adjustments = {}
        for i, name in enumerate(STAT_NAMES):
            promotion_adjustments[name] = struct.unpack(
                "b", bytes([data[stats_base + 24 + i]])
            )[0]

        # Advance to next entry: 96 + M*4 + S*4
        entry_size = 96 + M * 4 + S * 4
        pos += entry_size

        # Resolve weapon ranks strings
        base_weapon_ranks = resolve_string(data, base_wpn_ranks_ptr) or ""
        max_weapon_ranks = resolve_string(data, max_wpn_ranks_ptr) or ""

        classes.append({
            "jid": resolve_string(data, jid_ptr) or "",
            "mjid": resolve_string(data, mjid_ptr) or "",
            "weapon_ranks": base_weapon_ranks,
            "max_weapon_ranks": max_weapon_ranks,
            "constitution": constitution,
            "armor_type": armor_type,
            "weight": weight,
            "mount_type": mount_type,
            "mount_weight": mount_weight,
            "skill_count": skill_count,
            "skill_ids": skill_ids,
            "satori_skill": satori_skill,
            "attr_count": attr_count,
            "attributes": attributes,
            "skill_capacity": skill_capacity,
            "default_movement": default_movement,
            "promote_level": promote_level,
            "movement_type": movement_type,
            "vision_range": vision_range,
            "max_stats": max_stats,
            "base_stats": base_stats,
            "class_growth_rates": class_growth_rates,
            "promotion_adjustments": promotion_adjustments,
            "byte_offset": entry_start,
            "max_stats_offset": max_stats_offset,
        })

    return classes
