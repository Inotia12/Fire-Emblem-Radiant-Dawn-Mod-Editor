"""Parse the PersonData section from decompressed FE10Data binary.

PersonData entries start at offset 0x2C. The first 4 bytes are the entry count
(u32 BE). Each entry is variable-length: 80 + (skill_count * 4) bytes.

Entry structure (offsets relative to entry start):
  0:     skill_count (u8)
  1:     null
  2:     level (u8)
  3:     gender (u8)
  4-7:   PID pointer
  8-11:  MPID pointer
  12-15: MNPID pointer
  16-19: FID pointer
  20-23: JID pointer
  24-27: Affinity pointer
  28-31: Weapon ranks pointer
  32...: N skill ID pointers (4 bytes each)
  +N*4:  4 bytes null padding
  +4:    16 bytes animation pointers (4 pointers)
  then:  biorhythm_type (u8), 2 unknown flags, playability_flag (u8),
         authority_stars (u8), 4 laguz gauge bytes (i8),
         10 stat adjustment bytes (i8), 8 growth rate bytes (u8)
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

PERSON_DATA_OFFSET = 0x2C


def parse_all_characters(data: bytes) -> list[dict]:
    count = struct.unpack(">I", data[PERSON_DATA_OFFSET:PERSON_DATA_OFFSET + 4])[0]
    pos = PERSON_DATA_OFFSET + 4
    characters = []

    for _ in range(count):
        entry_start = pos
        skill_count = data[pos]
        level = data[pos + 2]
        gender = data[pos + 3]

        pid_ptr = struct.unpack(">I", data[pos + 4:pos + 8])[0]
        mpid_ptr = struct.unpack(">I", data[pos + 8:pos + 12])[0]
        mnpid_ptr = struct.unpack(">I", data[pos + 12:pos + 16])[0]
        fid_ptr = struct.unpack(">I", data[pos + 16:pos + 20])[0]
        jid_ptr = struct.unpack(">I", data[pos + 20:pos + 24])[0]
        affinity_ptr = struct.unpack(">I", data[pos + 24:pos + 28])[0]
        weapon_ranks_ptr = struct.unpack(">I", data[pos + 28:pos + 32])[0]

        skill_ids = []
        skill_slot_offsets = []
        for s in range(skill_count):
            slot_off = pos + 32 + s * 4
            skill_slot_offsets.append(slot_off)
            sid_ptr = struct.unpack(">I", data[slot_off:slot_off + 4])[0]
            skill_ids.append(resolve_string(data, sid_ptr))

        base = pos + 32 + skill_count * 4 + 4  # +4 null padding
        base += 16  # 4 animation pointers

        biorhythm_type = data[base]
        playability_flag = data[base + 3]
        authority_stars = data[base + 4]

        laguz_gauge = {
            "gain_turn": struct.unpack("b", bytes([data[base + 5]]))[0],
            "gain_battle": struct.unpack("b", bytes([data[base + 6]]))[0],
            "loss_turn": struct.unpack("b", bytes([data[base + 7]]))[0],
            "loss_battle": struct.unpack("b", bytes([data[base + 8]]))[0],
        }

        stat_adj_start = base + 9
        stat_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res", "con", "mov"]
        stat_adjustments = {}
        for i, name in enumerate(stat_names):
            stat_adjustments[name] = struct.unpack("b", bytes([data[stat_adj_start + i]]))[0]

        growth_start = stat_adj_start + 10
        growth_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]
        growth_rates = {}
        for i, name in enumerate(growth_names):
            growth_rates[name] = data[growth_start + i]

        entry_size = 80 + skill_count * 4
        pos += entry_size

        characters.append({
            "pid": resolve_string(data, pid_ptr) or "",
            "mpid": resolve_string(data, mpid_ptr) or "",
            "mnpid": resolve_string(data, mnpid_ptr) or "",
            "fid": resolve_string(data, fid_ptr) or "",
            "jid": resolve_string(data, jid_ptr) or "",
            "affinity": resolve_string(data, affinity_ptr) or "",
            "weapon_ranks": resolve_string(data, weapon_ranks_ptr) or "",
            "level": level,
            "gender": gender,
            "skill_count": skill_count,
            "skill_ids": skill_ids,
            "skill_slot_offsets": skill_slot_offsets,
            "biorhythm_type": biorhythm_type,
            "playability_flag": playability_flag,
            "authority_stars": authority_stars,
            "laguz_gauge": laguz_gauge,
            "stat_adjustments": stat_adjustments,
            "growth_rates": growth_rates,
            "byte_offset": entry_start,
        })

    return characters
