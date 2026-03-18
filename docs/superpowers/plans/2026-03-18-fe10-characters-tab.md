# FE10 Characters Tab — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a Characters tab to the FE10 Mod Editor that allows editing allied character stats, growth rates, equipped skills, biorhythm, laguz data, and class max stats.

**Architecture:** Three new core parsers (character, class, skill) feed three new model classes (CharacterDatabase, ClassDatabase, SkillDatabase). A Characters tab view with sub-tabbed side panel (Stats/Growths/Skills/Info) provides the editing UI. The existing ModBuilder and ProjectFile are extended to support character and class edits. A new "Class Changes" category is added to the Misc tab.

**Tech Stack:** Python 3.12+, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-fe10-characters-tab-design.md`

**Existing patterns to follow:** `core/item_parser.py` (parser), `models/item_data.py` (data model), `widgets/item_table.py` (table model), `widgets/item_editor.py` (side panel editor), `views/items_tab.py` (tab layout)

---

## File Structure

```
fe10_mod_editor/
├── core/
│   ├── character_parser.py         # Parse PersonData (461 entries at 0x2C)
│   ├── class_parser.py             # Parse JobData (171 entries at 0x926C)
│   └── skill_parser.py             # Parse SkillData (142 entries at 0x12810)
├── models/
│   ├── character_data.py           # CharacterEntry dataclass, CharacterDatabase
│   ├── class_data.py               # ClassEntry dataclass, ClassDatabase
│   └── skill_data.py               # SkillEntry dataclass, SkillDatabase
├── views/
│   ├── characters_tab.py           # Characters tab with sub-tabbed side panel
│   ├── misc_tab.py                 # MODIFY: add Class Changes category
│   └── main_window.py              # MODIFY: add Characters tab, load new data
├── widgets/
│   ├── character_table.py          # QAbstractTableModel for character list
│   ├── character_stats_editor.py   # Stats sub-tab (adjustments + computed finals)
│   ├── character_growths_editor.py # Growths sub-tab (8 growth rate fields)
│   ├── character_skills_editor.py  # Skills sub-tab (equipped list + add/remove)
│   └── character_info_editor.py    # Info sub-tab (biorhythm, laguz, max stats)
├── models/
│   ├── project.py                  # MODIFY: add character_edits, class_max_stat_edits, misc.class_changes
│   └── mod_builder.py              # MODIFY: apply character/class edits in build pipeline
└── tests/
    ├── test_character_parser.py
    ├── test_class_parser.py
    ├── test_skill_parser.py
    ├── test_character_data.py
    ├── test_class_data.py
    └── test_skill_data.py
```

---

## Task 1: Character Parser (`core/character_parser.py`)

**Files:**
- Create: `fe10_mod_editor/core/character_parser.py`
- Create: `fe10_mod_editor/tests/test_character_parser.py`

Parse the PersonData section from decompressed FE10Data. Follows the same pattern as `core/item_parser.py`.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_character_parser.py`:

```python
import os
import pytest
from fe10_mod_editor.core.character_parser import parse_all_characters, PERSON_DATA_OFFSET


def test_parse_all_characters_count(backup_dir):
    """Parse real FE10Data and expect 461 character entries."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    characters = parse_all_characters(data)
    assert len(characters) == 461


def test_parse_character_has_expected_fields(backup_dir):
    """Each parsed character has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    characters = parse_all_characters(data)
    first = characters[0]

    required_fields = [
        "pid", "mpid", "jid", "affinity", "level", "gender",
        "skill_ids", "biorhythm_type", "playability_flag",
        "authority_stars", "laguz_gauge", "stat_adjustments",
        "growth_rates", "byte_offset", "skill_count",
        "skill_slot_offsets",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_finds_playable_characters(backup_dir):
    """There should be ~73 characters with non-zero playability flag."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    characters = parse_all_characters(data)
    playable = [c for c in characters if c["playability_flag"] != 0]
    assert len(playable) >= 50  # At least 50 playable characters
    assert len(playable) <= 100  # But not more than 100
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_character_parser.py -v`
Expected: FAIL — ModuleNotFoundError

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/character_parser.py`:

```python
"""Parse the PersonData section from decompressed FE10Data binary.

PersonData entries start at offset 0x2C. The first 4 bytes are the entry count
(u32 BE). Each entry is variable-length: 79 + (skill_count * 4) bytes.

See spec for full byte layout.
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

PERSON_DATA_OFFSET = 0x2C


def parse_all_characters(data: bytes) -> list[dict]:
    """Parse all character entries from decompressed FE10Data.

    Returns list of dicts with all parsed fields. Each dict includes
    'byte_offset' for binary editing and 'skill_slot_offsets' listing
    the byte positions of each skill pointer slot.
    """
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

        # Skill ID pointers (variable count)
        skill_ids = []
        skill_slot_offsets = []
        for s in range(skill_count):
            slot_off = pos + 32 + s * 4
            skill_slot_offsets.append(slot_off)
            sid_ptr = struct.unpack(">I", data[slot_off:slot_off + 4])[0]
            sid = resolve_string(data, sid_ptr)
            skill_ids.append(sid)

        # Fixed fields after skills
        base = pos + 32 + skill_count * 4 + 4  # +4 for null padding

        # 4 animation pointers (16 bytes) — skip, just advance
        base += 16

        biorhythm_type = data[base]
        # base+1, base+2: unknown flags
        playability_flag = data[base + 3]
        authority_stars = data[base + 4]

        # Laguz transform modifiers (4 signed bytes)
        laguz_gauge = {
            "gain_turn": struct.unpack("b", bytes([data[base + 5]]))[0],
            "gain_battle": struct.unpack("b", bytes([data[base + 6]]))[0],
            "loss_turn": struct.unpack("b", bytes([data[base + 7]]))[0],
            "loss_battle": struct.unpack("b", bytes([data[base + 8]]))[0],
        }

        # Stat adjustments (10 signed bytes)
        stat_adj_start = base + 9
        stat_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res", "con", "mov"]
        stat_adjustments = {}
        for i, name in enumerate(stat_names):
            val = struct.unpack("b", bytes([data[stat_adj_start + i]]))[0]
            stat_adjustments[name] = val

        # Growth rates (8 unsigned bytes)
        growth_start = stat_adj_start + 10
        growth_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]
        growth_rates = {}
        for i, name in enumerate(growth_names):
            growth_rates[name] = data[growth_start + i]

        entry_size = 79 + skill_count * 4
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_character_parser.py -v`
Expected: All 3 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/character_parser.py fe10_mod_editor/tests/test_character_parser.py
git commit -m "feat: add character parser for PersonData section (461 entries)"
```

---

## Task 2: Class Parser (`core/class_parser.py`)

**Files:**
- Create: `fe10_mod_editor/core/class_parser.py`
- Create: `fe10_mod_editor/tests/test_class_parser.py`

Parse the JobData section. Follows item_parser pattern but with the more complex variable-length class entry structure.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_class_parser.py`:

```python
import os
import pytest
from fe10_mod_editor.core.class_parser import parse_all_classes, JOB_DATA_OFFSET


def test_parse_all_classes_count(backup_dir):
    """Parse real FE10Data and expect 171 class entries."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    classes = parse_all_classes(data)
    assert len(classes) == 171


def test_parse_class_has_expected_fields(backup_dir):
    """Each parsed class has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    classes = parse_all_classes(data)
    first = classes[0]

    required_fields = [
        "jid", "mjid", "skill_capacity", "default_movement",
        "max_stats", "base_stats", "class_growth_rates",
        "byte_offset", "max_stats_offset",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_class_max_stats_are_reasonable(backup_dir):
    """Max stats should be in a reasonable range (20-60 typically)."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    classes = parse_all_classes(data)
    # Find a class that should have reasonable max stats
    for cls in classes:
        if cls["jid"] and "JID" in cls["jid"]:
            max_hp = cls["max_stats"]["hp"]
            # Max HP should be between 20 and 120
            assert 20 <= max_hp <= 120, f"{cls['jid']} has max HP={max_hp}"
            break
```

- [ ] **Step 2: Run tests to verify they fail, then write implementation**

Create `fe10_mod_editor/core/class_parser.py`:

```python
"""Parse the JobData section from decompressed FE10Data binary.

JobData entries start at offset 0x926C. The first 4 bytes are the entry count
(171, u32 BE). Each entry is variable-length: 92 + (M*4) + (S*4) bytes.
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

JOB_DATA_OFFSET = 0x926C


def parse_all_classes(data: bytes) -> list[dict]:
    """Parse all class entries from decompressed FE10Data.

    Returns list of dicts. Each includes 'max_stats_offset' pointing to the
    byte position of the max stats block (needed for binary editing).
    """
    count = struct.unpack(">I", data[JOB_DATA_OFFSET:JOB_DATA_OFFSET + 4])[0]
    pos = JOB_DATA_OFFSET + 4
    classes = []

    for _ in range(count):
        entry_start = pos

        jid_ptr = struct.unpack(">I", data[pos:pos + 4])[0]
        mjid_ptr = struct.unpack(">I", data[pos + 4:pos + 8])[0]

        # Fixed header fields
        constitution = data[pos + 44]
        armor_type = data[pos + 45]
        armor_weight = data[pos + 46]
        mount_type = data[pos + 47]
        mount_weight = data[pos + 48]
        skill_count_m = data[pos + 49]
        sfxc_count_s = data[pos + 50]
        promote_level = data[pos + 51]
        movement_type = data[pos + 52]
        default_movement = data[pos + 53]
        skill_capacity = data[pos + 54]
        vision_range = data[pos + 55]

        # Variable: skill pointers + satori sign + sfxc pointers
        skills_start = pos + 56
        satori_off = skills_start + skill_count_m * 4
        sfxc_start = satori_off + 4
        stats_start = sfxc_start + sfxc_count_s * 4

        # Max stats (8 unsigned bytes)
        max_stats_offset = stats_start
        stat_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]
        max_stats = {name: data[stats_start + i] for i, name in enumerate(stat_names)}

        # Base stats (8 signed bytes)
        base_off = stats_start + 8
        base_stats = {}
        for i, name in enumerate(stat_names):
            base_stats[name] = struct.unpack("b", bytes([data[base_off + i]]))[0]

        # Class growth rates (8 unsigned bytes)
        growth_off = base_off + 8
        class_growth_rates = {name: data[growth_off + i] for i, name in enumerate(stat_names)}

        # Promotion stat adjustments (8 signed bytes)
        promo_off = growth_off + 8

        entry_size = 92 + skill_count_m * 4 + sfxc_count_s * 4
        pos += entry_size

        # Weapon ranks pointers
        base_wranks_ptr = struct.unpack(">I", data[pos + 36:pos + 40])[0]  # Before entry_start adjustment
        # Note: pos was already set to entry_start at loop top, use entry_start for these
        base_wranks_ptr = struct.unpack(">I", data[entry_start + 36:entry_start + 40])[0]

        classes.append({
            "jid": resolve_string(data, jid_ptr) or "",
            "mjid": resolve_string(data, mjid_ptr) or "",
            "weapon_ranks": resolve_string(data, base_wranks_ptr) or "",
            "constitution": constitution,
            "skill_capacity": skill_capacity,
            "default_movement": default_movement,
            "promote_level": promote_level,
            "vision_range": vision_range,
            "max_stats": max_stats,
            "base_stats": base_stats,
            "class_growth_rates": class_growth_rates,
            "byte_offset": entry_start,
            "max_stats_offset": max_stats_offset,
        })

    return classes
```

- [ ] **Step 3: Run tests, then commit**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_class_parser.py -v`

```bash
git add fe10_mod_editor/core/class_parser.py fe10_mod_editor/tests/test_class_parser.py
git commit -m "feat: add class parser for JobData section (171 entries)"
```

---

## Task 3: Skill Parser (`core/skill_parser.py`)

**Files:**
- Create: `fe10_mod_editor/core/skill_parser.py`
- Create: `fe10_mod_editor/tests/test_skill_parser.py`

Parse the SkillData section. Fixed-size entries (0x2C = 44 bytes each) with restriction table pointers.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_skill_parser.py`:

```python
import os
import pytest
from fe10_mod_editor.core.skill_parser import parse_all_skills, SKILL_DATA_OFFSET


def test_parse_all_skills_count(backup_dir):
    """Parse real FE10Data and expect 142 skill entries."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    skills = parse_all_skills(data)
    assert len(skills) == 142


def test_parse_skill_has_expected_fields(backup_dir):
    """Each parsed skill has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    skills = parse_all_skills(data)
    first = skills[0]

    required_fields = [
        "sid", "msid", "capacity_cost", "visibility",
        "whitelist", "blacklist",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_skill_capacity_costs_reasonable(backup_dir):
    """Skill capacity costs should be in a reasonable range."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    skills = parse_all_skills(data)
    for skill in skills:
        assert -50 <= skill["capacity_cost"] <= 50, f"{skill['sid']} cost={skill['capacity_cost']}"
```

- [ ] **Step 2: Run tests, write implementation, run tests, commit**

Create `fe10_mod_editor/core/skill_parser.py`:

```python
"""Parse the SkillData section from decompressed FE10Data binary.

SkillData entries start at offset 0x12810. Each entry is 0x2C (44) bytes.
Restriction tables are stored separately, referenced by pointers.
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string

SKILL_DATA_OFFSET = 0x12810
SKILL_ENTRY_SIZE = 0x2C  # 44 bytes


def parse_all_skills(data: bytes) -> list[dict]:
    """Parse all skill entries from decompressed FE10Data."""
    count = struct.unpack(">I", data[SKILL_DATA_OFFSET:SKILL_DATA_OFFSET + 4])[0]
    pos = SKILL_DATA_OFFSET + 4
    skills = []

    for _ in range(count):
        sid_ptr = struct.unpack(">I", data[pos:pos + 4])[0]
        msid_ptr = struct.unpack(">I", data[pos + 4:pos + 8])[0]

        capacity_cost = struct.unpack("b", bytes([data[pos + 30]]))[0]
        visibility = data[pos + 29]

        # Restriction tables
        table1_count = data[pos + 32]
        table2_count = data[pos + 33]
        table1_ptr = struct.unpack(">I", data[pos + 34:pos + 38])[0]
        table2_ptr = struct.unpack(">I", data[pos + 38:pos + 42])[0]

        whitelist = _parse_restriction_table(data, table1_ptr, table1_count)
        blacklist = _parse_restriction_table(data, table2_ptr, table2_count)

        pos += SKILL_ENTRY_SIZE

        skills.append({
            "sid": resolve_string(data, sid_ptr) or "",
            "msid": resolve_string(data, msid_ptr) or "",
            "capacity_cost": capacity_cost,
            "visibility": visibility,
            "whitelist": whitelist,
            "blacklist": blacklist,
        })

    return skills


def _parse_restriction_table(data: bytes, ptr: int, count: int) -> list[str]:
    """Parse a skill restriction table, returning list of ID strings."""
    if ptr == 0 or count == 0:
        return []

    offset = ptr + 0x20
    results = []
    for i in range(count):
        entry_off = offset + i * 8
        # flag = data[entry_off]  # 0x0=whitelist, 0x1=blacklist (already separated by table)
        id_ptr = struct.unpack(">I", data[entry_off + 4:entry_off + 8])[0]
        id_str = resolve_string(data, id_ptr)
        if id_str:
            results.append(id_str)
    return results
```

Run and commit:
```bash
cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_skill_parser.py -v
git add fe10_mod_editor/core/skill_parser.py fe10_mod_editor/tests/test_skill_parser.py
git commit -m "feat: add skill parser for SkillData section (142 entries)"
```

---

## Task 4: Character Data Model (`models/character_data.py`)

**Files:**
- Create: `fe10_mod_editor/models/character_data.py`
- Create: `fe10_mod_editor/tests/test_character_data.py`

- [ ] **Step 1: Write tests**

```python
import os
import pytest
from fe10_mod_editor.models.character_data import CharacterEntry, CharacterDatabase


def test_character_entry_display_name():
    ch = CharacterEntry(
        pid="PID_IKE", mpid="MPID_IKE", jid="JID_HERO",
        level=11, gender=0, skill_count=2, skill_ids=["SID_AETHER", "SID_SHOVE"],
        skill_slot_offsets=[100, 104], biorhythm_type=2, playability_flag=0x1F,
        authority_stars=0, laguz_gauge={"gain_turn": 0, "gain_battle": 0, "loss_turn": 0, "loss_battle": 0},
        stat_adjustments={"hp": 6, "str": 2, "mag": -1, "skl": 3, "spd": 1, "lck": 4, "def": 1, "res": -3, "con": 0, "mov": 0},
        growth_rates={"hp": 65, "str": 55, "mag": 10, "skl": 60, "spd": 35, "lck": 30, "def": 40, "res": 15},
        byte_offset=0x30,
    )
    assert ch.display_name == "Ike"
    assert ch.is_playable is True
    assert ch.is_laguz is False


def test_character_database_filtering(backup_dir):
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.character_parser import parse_all_characters

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    db = CharacterDatabase.from_parsed(parse_all_characters(data))
    assert db.count == 461
    assert len(db.allied_characters) >= 50
    assert len(db.allied_characters) <= 100
    assert db.get("PID_IKE") is not None or len([c for c in db.all_characters if "IKE" in c.pid]) > 0
```

- [ ] **Step 2: Write implementation**

Create `fe10_mod_editor/models/character_data.py`:

```python
"""Character data model — wraps parsed character data with display logic and filtering."""

from dataclasses import dataclass, field


def display_name_from_pid(pid: str) -> str:
    """Convert PID to display name: strip 'PID_', replace '_', title case."""
    name = pid
    if name.startswith("PID_"):
        name = name[4:]
    return name.replace("_", " ").title()


@dataclass
class CharacterEntry:
    pid: str
    mpid: str
    jid: str
    level: int
    gender: int
    skill_count: int
    skill_ids: list[str | None] = field(default_factory=list)
    skill_slot_offsets: list[int] = field(default_factory=list)
    biorhythm_type: int = 0
    playability_flag: int = 0
    authority_stars: int = 0
    laguz_gauge: dict = field(default_factory=dict)
    stat_adjustments: dict = field(default_factory=dict)
    growth_rates: dict = field(default_factory=dict)
    byte_offset: int = 0
    # Additional resolved fields (populated by CharacterDatabase)
    affinity: str = ""
    fid: str = ""

    @property
    def display_name(self) -> str:
        return display_name_from_pid(self.pid)

    @property
    def is_playable(self) -> bool:
        return self.playability_flag != 0

    @property
    def is_laguz(self) -> bool:
        g = self.laguz_gauge
        return any(g.get(k, 0) != 0 for k in ["gain_turn", "gain_battle", "loss_turn", "loss_battle"])


class CharacterDatabase:
    def __init__(self, characters: list[CharacterEntry]):
        self._characters = characters
        self._by_pid = {c.pid: c for c in characters}

    @classmethod
    def from_parsed(cls, parsed: list[dict]) -> "CharacterDatabase":
        entries = [
            CharacterEntry(
                pid=p["pid"], mpid=p["mpid"], jid=p["jid"],
                level=p["level"], gender=p["gender"],
                skill_count=p["skill_count"], skill_ids=p["skill_ids"],
                skill_slot_offsets=p["skill_slot_offsets"],
                biorhythm_type=p["biorhythm_type"],
                playability_flag=p["playability_flag"],
                authority_stars=p["authority_stars"],
                laguz_gauge=p["laguz_gauge"],
                stat_adjustments=p["stat_adjustments"],
                growth_rates=p["growth_rates"],
                byte_offset=p["byte_offset"],
                affinity=p.get("affinity", ""),
                fid=p.get("fid", ""),
            )
            for p in parsed
        ]
        return cls(entries)

    @property
    def count(self) -> int:
        return len(self._characters)

    @property
    def all_characters(self) -> list[CharacterEntry]:
        return list(self._characters)

    @property
    def allied_characters(self) -> list[CharacterEntry]:
        return [c for c in self._characters if c.is_playable]

    @property
    def laguz_characters(self) -> list[CharacterEntry]:
        return [c for c in self._characters if c.is_laguz]

    @property
    def beorc_characters(self) -> list[CharacterEntry]:
        return [c for c in self._characters if not c.is_laguz]

    def get(self, pid: str) -> CharacterEntry | None:
        return self._by_pid.get(pid)
```

- [ ] **Step 3: Run tests, commit**

```bash
cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_character_data.py -v
git add fe10_mod_editor/models/character_data.py fe10_mod_editor/tests/test_character_data.py
git commit -m "feat: add CharacterEntry dataclass and CharacterDatabase with allied/laguz filtering"
```

---

## Task 5: Class Data Model + Skill Data Model

**Files:**
- Create: `fe10_mod_editor/models/class_data.py`
- Create: `fe10_mod_editor/models/skill_data.py`
- Create: `fe10_mod_editor/tests/test_class_data.py`
- Create: `fe10_mod_editor/tests/test_skill_data.py`

Two small models that wrap parsed class and skill data. Follow the same pattern as CharacterDatabase.

- [ ] **Step 1: Write tests for both**

`test_class_data.py`:
```python
import os
import pytest
from fe10_mod_editor.models.class_data import ClassEntry, ClassDatabase


def test_class_database_from_parsed(backup_dir):
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.class_parser import parse_all_classes

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    db = ClassDatabase.from_parsed(parse_all_classes(data))
    assert db.count == 171
    # Should be able to look up by JID
    assert len(db.all_classes) == 171
```

`test_skill_data.py`:
```python
import os
import pytest
from fe10_mod_editor.models.skill_data import SkillEntry, SkillDatabase


def test_skill_database_from_parsed(backup_dir):
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.skill_parser import parse_all_skills

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    db = SkillDatabase.from_parsed(parse_all_skills(data))
    assert db.count == 142


def test_skill_restriction_check(backup_dir):
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.skill_parser import parse_all_skills

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        data = decompress_lz10(f.read())

    db = SkillDatabase.from_parsed(parse_all_skills(data))
    # check_restriction should return a string warning or None
    for skill in db.all_skills:
        result = db.check_restriction(skill.sid, "JID_HERO")
        assert result is None or isinstance(result, str)
```

- [ ] **Step 2: Write both implementations**

`models/class_data.py`:
```python
"""Class data model — wraps parsed JobData with lookup by JID."""

from dataclasses import dataclass, field


@dataclass
class ClassEntry:
    jid: str
    mjid: str
    skill_capacity: int
    default_movement: int
    max_stats: dict = field(default_factory=dict)
    base_stats: dict = field(default_factory=dict)
    class_growth_rates: dict = field(default_factory=dict)
    max_stats_offset: int = 0
    byte_offset: int = 0
    constitution: int = 0
    promote_level: int = 0
    weapon_ranks: str = ""

    @property
    def display_name(self) -> str:
        name = self.jid
        if name.startswith("JID_"):
            name = name[4:]
        return name.replace("_", " ").title()


class ClassDatabase:
    def __init__(self, classes: list[ClassEntry]):
        self._classes = classes
        self._by_jid = {c.jid: c for c in classes}

    @classmethod
    def from_parsed(cls, parsed: list[dict]) -> "ClassDatabase":
        entries = [
            ClassEntry(
                jid=p["jid"], mjid=p["mjid"],
                skill_capacity=p["skill_capacity"],
                default_movement=p["default_movement"],
                max_stats=p["max_stats"],
                base_stats=p["base_stats"],
                class_growth_rates=p["class_growth_rates"],
                max_stats_offset=p["max_stats_offset"],
                byte_offset=p["byte_offset"],
                constitution=p.get("constitution", 0),
                promote_level=p.get("promote_level", 0),
                weapon_ranks=p.get("weapon_ranks", ""),
            )
            for p in parsed
        ]
        return cls(entries)

    @property
    def count(self) -> int:
        return len(self._classes)

    @property
    def all_classes(self) -> list[ClassEntry]:
        return list(self._classes)

    def get(self, jid: str) -> ClassEntry | None:
        return self._by_jid.get(jid)
```

`models/skill_data.py`:
```python
"""Skill data model — wraps parsed SkillData with restriction checking."""

from dataclasses import dataclass, field


@dataclass
class SkillEntry:
    sid: str
    msid: str
    capacity_cost: int
    visibility: int
    whitelist: list[str] = field(default_factory=list)
    blacklist: list[str] = field(default_factory=list)

    @property
    def display_name(self) -> str:
        name = self.sid
        if name.startswith("SID_"):
            name = name[4:]
        return name.replace("_", " ").title()

    @property
    def is_visible(self) -> bool:
        return self.visibility != 3  # 3 = hidden


class SkillDatabase:
    def __init__(self, skills: list[SkillEntry]):
        self._skills = skills
        self._by_sid = {s.sid: s for s in skills}

    @classmethod
    def from_parsed(cls, parsed: list[dict]) -> "SkillDatabase":
        entries = [
            SkillEntry(
                sid=p["sid"], msid=p["msid"],
                capacity_cost=p["capacity_cost"],
                visibility=p["visibility"],
                whitelist=p["whitelist"],
                blacklist=p["blacklist"],
            )
            for p in parsed
        ]
        return cls(entries)

    @property
    def count(self) -> int:
        return len(self._skills)

    @property
    def all_skills(self) -> list[SkillEntry]:
        return list(self._skills)

    def get(self, sid: str) -> SkillEntry | None:
        return self._by_sid.get(sid)

    def check_restriction(self, sid: str, jid: str) -> str | None:
        """Check if a skill has class restrictions for the given JID.

        Returns a warning string if restricted, None if OK.
        """
        skill = self._by_sid.get(sid)
        if skill is None:
            return None
        if skill.whitelist and jid not in skill.whitelist:
            return f"This skill is not normally available to {jid} class"
        if jid in skill.blacklist:
            return f"This skill is blocked for {jid} class"
        return None
```

- [ ] **Step 3: Run tests, commit**

```bash
cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_class_data.py fe10_mod_editor/tests/test_skill_data.py -v
git add fe10_mod_editor/models/class_data.py fe10_mod_editor/models/skill_data.py fe10_mod_editor/tests/test_class_data.py fe10_mod_editor/tests/test_skill_data.py
git commit -m "feat: add ClassDatabase and SkillDatabase models with restriction checking"
```

---

## Task 6: Extend ProjectFile (`models/project.py`)

**Files:**
- Modify: `fe10_mod_editor/models/project.py`
- Modify: `fe10_mod_editor/tests/test_project.py`

Add `character_edits`, `class_max_stat_edits`, and `misc.class_changes` fields.

- [ ] **Step 1: Add test**

Add to `test_project.py`:

```python
def test_project_character_edits_roundtrip(tmp_path):
    proj = ProjectFile.new()
    proj.character_edits["PID_IKE"] = {
        "level": 15,
        "stat_adjustments": {"hp": 10, "str": 5},
        "growth_rates": {"hp": 70},
        "skills": ["SID_AETHER"],
    }
    proj.class_max_stat_edits["JID_HERO"] = {"hp": 60, "str": 40}
    proj.misc["class_changes"] = {"set_all_max_stats": True, "max_stats_preset": 60}

    path = str(tmp_path / "test.fe10mod")
    proj.save(path)
    loaded = ProjectFile.load(path)

    assert loaded.character_edits["PID_IKE"]["level"] == 15
    assert loaded.class_max_stat_edits["JID_HERO"]["hp"] == 60
    assert loaded.misc["class_changes"]["set_all_max_stats"] is True
```

- [ ] **Step 2: Modify ProjectFile**

In `project.py`, add to `__init__`:
```python
self.character_edits: dict[str, dict] = {}
self.class_max_stat_edits: dict[str, dict] = {}
# Add to misc:
self.misc["class_changes"] = {
    "set_all_max_stats": False,
    "max_stats_preset": 40,
}
```

Update `save()` to include the new fields. Update `load()` to read them with defaults.

- [ ] **Step 3: Run tests, commit**

```bash
cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_project.py -v
git add fe10_mod_editor/models/project.py fe10_mod_editor/tests/test_project.py
git commit -m "feat: extend ProjectFile with character_edits, class_max_stat_edits, class_changes"
```

---

## Task 7: Extend ModBuilder for Character/Class Edits

**Files:**
- Modify: `fe10_mod_editor/models/mod_builder.py`
- Modify: `fe10_mod_editor/tests/test_mod_builder.py`

Add character edit application, class max stat editing, and misc class changes to the build pipeline.

- [ ] **Step 1: Add test**

Add to `test_mod_builder.py`:

```python
def test_mod_builder_applies_character_growth_edit(build_env):
    """Build with a character growth edit should modify FE10Data."""
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.character_parser import parse_all_characters

    proj = ProjectFile.new()
    proj.paths["backup_dir"] = build_env["backup_dir"]
    proj.paths["game_dir"] = build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(build_env["backup_dir"])

    # Find a character PID from the backup data
    cms_path = os.path.join(build_env["backup_dir"], "FE10Data.cms")
    with open(cms_path, "rb") as f:
        orig_data = decompress_lz10(f.read())
    chars = parse_all_characters(orig_data)
    # Pick a playable character
    playable = [c for c in chars if c["playability_flag"] != 0]
    target_pid = playable[0]["pid"]

    proj.character_edits[target_pid] = {"growth_rates": {"hp": 99}}

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    # Verify the growth was changed
    output_cms = os.path.join(build_env["game_files"], "FE10Data.cms")
    with open(output_cms, "rb") as f:
        modded_data = decompress_lz10(f.read())

    modded_chars = parse_all_characters(modded_data)
    modded_char = next(c for c in modded_chars if c["pid"] == target_pid)
    assert modded_char["growth_rates"]["hp"] == 99
```

- [ ] **Step 2: Extend ModBuilder.build()**

Add new steps after existing item edits and before recompression:

```python
# Step 3b: Apply character edits
self._apply_character_edits(data, parsed_characters)

# Step 3c: Apply class max stat edits
self._apply_class_max_stat_edits(data, parsed_classes)

# Step 3d: Apply misc class changes (set all max stats)
self._apply_misc_class_changes(data, parsed_classes)
```

New private methods:

```python
def _apply_character_edits(self, data: bytearray, parsed_characters: list[dict]):
    """Apply per-character edits (stats, growths, level, authority, biorhythm, skills)."""
    edits = self.project.character_edits
    for char in parsed_characters:
        pid = char["pid"]
        if pid not in edits:
            continue
        char_edits = edits[pid]
        off = char["byte_offset"]
        n = char["skill_count"]

        # Level (offset +2)
        if "level" in char_edits:
            data[off + 2] = char_edits["level"]

        # Authority stars (offset 56+N*4)
        base = off + 32 + n * 4 + 4 + 16  # skip skills, null, animations
        if "authority_stars" in char_edits:
            data[base + 4] = char_edits["authority_stars"]

        # Biorhythm type (base+0)
        if "biorhythm_type" in char_edits:
            data[base] = char_edits["biorhythm_type"]

        # Laguz gauge (base+5 through base+8)
        if "laguz_gauge" in char_edits:
            gauge = char_edits["laguz_gauge"]
            for i, key in enumerate(["gain_turn", "gain_battle", "loss_turn", "loss_battle"]):
                if key in gauge:
                    struct.pack_into("b", data, base + 5 + i, gauge[key])

        # Stat adjustments (base+9, 10 signed bytes)
        if "stat_adjustments" in char_edits:
            stat_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res", "con", "mov"]
            for i, name in enumerate(stat_names):
                if name in char_edits["stat_adjustments"]:
                    struct.pack_into("b", data, base + 9 + i, char_edits["stat_adjustments"][name])

        # Growth rates (base+19, 8 unsigned bytes)
        if "growth_rates" in char_edits:
            growth_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]
            for i, name in enumerate(growth_names):
                if name in char_edits["growth_rates"]:
                    data[base + 19 + i] = char_edits["growth_rates"][name]

        # Skills (replace in existing slots, don't change count)
        if "skills" in char_edits:
            new_skills = char_edits["skills"]
            for slot_idx, slot_off in enumerate(char["skill_slot_offsets"]):
                if slot_idx < len(new_skills) and new_skills[slot_idx]:
                    # Need to find the SID pointer value — scan for it
                    sid_ptr = self._find_string_pointer(data, new_skills[slot_idx])
                    if sid_ptr is not None:
                        struct.pack_into(">I", data, slot_off, sid_ptr)
                else:
                    struct.pack_into(">I", data, slot_off, 0)

        self.log(f"  Character edited: {pid}")

def _apply_class_max_stat_edits(self, data: bytearray, parsed_classes: list[dict]):
    """Apply per-class max stat edits."""
    edits = self.project.class_max_stat_edits
    for cls in parsed_classes:
        jid = cls["jid"]
        if jid not in edits:
            continue
        max_off = cls["max_stats_offset"]
        stat_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]
        for i, name in enumerate(stat_names):
            if name in edits[jid]:
                data[max_off + i] = edits[jid][name]
        self.log(f"  Class max stats edited: {jid}")

def _apply_misc_class_changes(self, data: bytearray, parsed_classes: list[dict]):
    """Apply misc class changes (set all max stats preset)."""
    class_changes = self.project.misc.get("class_changes", {})
    if not class_changes.get("set_all_max_stats", False):
        return
    preset = class_changes.get("max_stats_preset", 40)
    stat_names = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]
    for cls in parsed_classes:
        max_off = cls["max_stats_offset"]
        for i, name in enumerate(stat_names):
            val = preset + 20 if name == "hp" else preset
            data[max_off + i] = min(val, 255)
    self.log(f"  All class max stats set to {preset} (HP: {preset + 20})")

def _find_string_pointer(self, data: bytes, target_string: str) -> int | None:
    """Find the CMS pointer value for a given string in the data."""
    encoded = target_string.encode("ascii") + b"\x00"
    idx = data.find(encoded)
    if idx == -1:
        return None
    return idx - 0x20  # CMS pointer convention
```

- [ ] **Step 3: Run tests, commit**

```bash
cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_mod_builder.py -v --timeout=600
git add fe10_mod_editor/models/mod_builder.py fe10_mod_editor/tests/test_mod_builder.py
git commit -m "feat: extend ModBuilder with character edits, class max stats, and preset toggle"
```

---

## Task 8: Character Table Widget (`widgets/character_table.py`)

**Files:**
- Create: `fe10_mod_editor/widgets/character_table.py`

Follows the exact same pattern as `widgets/item_table.py` but for characters. No automated tests (UI widget).

- [ ] **Step 1: Write implementation**

Create `fe10_mod_editor/widgets/character_table.py` with:

- `CharacterTableModel(QAbstractTableModel)` — columns: Name, Class, Lv, HP, Str, Mag, Skl, Spd, Lck, Def, Res
- Stats shown are computed finals (class base + adjustment), using class_database for lookup
- `character_edits` overlay for modified values
- Modified rows get yellow background via `Qt.BackgroundRole`
- `CharacterSortFilterProxy(QSortFilterProxyModel)` — filters: search text, character type (allied/all/laguz/beorc)
- `set_data_source(char_db, class_db, character_edits)` method
- `set_filter(filter_type: str)` — "allied", "all", "laguz", "beorc"
- `set_search_text(text: str)`

The model needs both `CharacterDatabase` and `ClassDatabase` to compute final stats.

- [ ] **Step 2: Verify imports**

```bash
python -c "from fe10_mod_editor.widgets.character_table import CharacterTableModel; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add fe10_mod_editor/widgets/character_table.py
git commit -m "feat: add character table widget with filter and computed stat display"
```

---

## Task 9: Character Editor Sub-Tab Widgets

**Files:**
- Create: `fe10_mod_editor/widgets/character_stats_editor.py`
- Create: `fe10_mod_editor/widgets/character_growths_editor.py`
- Create: `fe10_mod_editor/widgets/character_skills_editor.py`
- Create: `fe10_mod_editor/widgets/character_info_editor.py`

Four side panel sub-tab widgets following the `ItemEditor` pattern. Each emits a `field_changed` signal.

- [ ] **Step 1: Write CharacterStatsEditor**

Stats sub-tab: 10 stat rows (each with Final label + Adjustment QSpinBox + Class Base label), plus Level and Authority QSpinBoxes. Uses `_loading` flag pattern from ItemEditor.

Emits `field_changed(pid, field_path, value)` — field_path uses dot notation like `"stat_adjustments.hp"` or `"level"`.

- [ ] **Step 2: Write CharacterGrowthsEditor**

Growths sub-tab: 8 QSpinBox fields (0-255) with class growth reference tooltips. Yellow highlight if > 100%.

Emits `field_changed(pid, field_path, value)` — e.g., `"growth_rates.hp"`.

- [ ] **Step 3: Write CharacterSkillsEditor**

Skills sub-tab: capacity counter label, equipped skills list (QTableWidget with Name, Cost, Remove button columns), searchable "Add Skill" QComboBox at the bottom. Needs SkillDatabase reference for names/costs/restrictions. Shows warning labels for class-restricted skills.

Emits `field_changed(pid, "skills", skill_list)` with the full updated skill list.

Respects skill replacement strategy: max equipped = original skill_count. Add button disabled when all slots full.

- [ ] **Step 4: Write CharacterInfoEditor**

Info sub-tab: read-only character info (PID, gender), read-only class info (name, movement, skill capacity), editable max stats (8 QSpinBoxes with "affects all [Class] characters" warning), biorhythm dropdown, laguz data section (4 QSpinBoxes, hidden for non-laguz).

Max stats QSpinBoxes are disabled when misc "set_all_max_stats" is active.

Emits `field_changed` for biorhythm, laguz gauge, and max stats.

- [ ] **Step 5: Verify imports**

```bash
python -c "
from fe10_mod_editor.widgets.character_stats_editor import CharacterStatsEditor
from fe10_mod_editor.widgets.character_growths_editor import CharacterGrowthsEditor
from fe10_mod_editor.widgets.character_skills_editor import CharacterSkillsEditor
from fe10_mod_editor.widgets.character_info_editor import CharacterInfoEditor
print('All OK')
"
```

- [ ] **Step 6: Commit**

```bash
git add fe10_mod_editor/widgets/character_stats_editor.py fe10_mod_editor/widgets/character_growths_editor.py fe10_mod_editor/widgets/character_skills_editor.py fe10_mod_editor/widgets/character_info_editor.py
git commit -m "feat: add character editor sub-tab widgets (stats, growths, skills, info)"
```

---

## Task 10: Characters Tab View (`views/characters_tab.py`)

**Files:**
- Create: `fe10_mod_editor/views/characters_tab.py`

Follows `views/items_tab.py` pattern with QSplitter layout and sub-tabbed right panel.

- [ ] **Step 1: Write implementation**

`CharactersTab(QWidget)` with:
- Left side: search QLineEdit + filter QComboBox (Allied/All/Laguz/Beorc) + CharacterTableModel in QTableView
- Right side: QTabWidget with 4 sub-tabs (Stats, Growths, Skills, Info editors)
- Header area above sub-tabs showing character name, PID, class, level
- "Reset to Original" button at bottom

Signal connections:
- Table row selection → load character into all 4 editor sub-tabs
- Editor field changes → update `project.character_edits[pid]` or `project.class_max_stat_edits[jid]`
- Filter/search → proxy model

`set_data(char_db, class_db, skill_db, project)` method for data loading.

- [ ] **Step 2: Verify imports**

```bash
python -c "from fe10_mod_editor.views.characters_tab import CharactersTab; print('OK')"
```

- [ ] **Step 3: Commit**

```bash
git add fe10_mod_editor/views/characters_tab.py
git commit -m "feat: add Characters tab with sub-tabbed side panel"
```

---

## Task 11: Wire Characters Tab into Main Window + Extend Misc Tab

**Files:**
- Modify: `fe10_mod_editor/views/main_window.py`
- Modify: `fe10_mod_editor/views/misc_tab.py`

- [ ] **Step 1: Add Characters tab to main_window.py**

1. Import `CharactersTab`
2. Add `self.character_database`, `self.class_database`, `self.skill_database` fields
3. Add `self._decompressed_fe10data: bytes | None = None` field — cache the decompressed buffer
4. Modify `_load_item_database()` to store `self._decompressed_fe10data = data` after decompression so it can be reused
5. Insert Characters tab between Shops and Misc (index 3). **Update misc_index from 3 to 4** in `_refresh_misc_tab` and any other hardcoded tab indices.
6. Add `_load_character_data()` — parse characters, classes, skills from `self._decompressed_fe10data` (already decompressed for items, no double decompression)
5. Add `_refresh_characters_tab()` — pass all databases and project to the tab
7. Wire loading into `_on_game_directory_ready()` flow
8. Update `_on_new()` to reset `character_database`, `class_database`, `skill_database`, `_decompressed_fe10data` to None and refresh the characters tab

- [ ] **Step 2: Add Class Changes category to misc_tab.py**

Add after WEAPON_CHANGES:

```python
CLASS_CHANGES = [
    {
        "key": "set_all_max_stats",
        "title": "Set All Max Stats",
        "description": "Sets every class's max stat caps to the selected value "
                       "(+20 for HP). Individual max stat edits are preserved "
                       "but suppressed while this is active.",
        "count": 171,
    },
]
```

Add a "Class Changes" section header and the toggle card. Also add a preset QComboBox (40/60/80/Custom) and a custom QSpinBox that appear below the toggle card when it's enabled. Connect changes to `project.misc["class_changes"]`.

- [ ] **Step 3: Verify imports and test**

```bash
python -c "from fe10_mod_editor.views.main_window import MainWindow; print('OK')"
```

- [ ] **Step 4: Commit**

```bash
git add fe10_mod_editor/views/main_window.py fe10_mod_editor/views/misc_tab.py
git commit -m "feat: wire Characters tab into main window and add Class Changes to Misc tab"
```

---

## Task 12: Integration Test + Polish

**Files:**
- Create: `fe10_mod_editor/tests/test_character_integration.py`
- Possibly modify: any files with bugs found

- [ ] **Step 1: Write integration test**

```python
import os
import tempfile
import shutil
import pytest
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.mod_builder import ModBuilder
from fe10_mod_editor.core.backup_manager import compute_backup_hashes
from fe10_mod_editor.core.lz10 import decompress_lz10
from fe10_mod_editor.core.character_parser import parse_all_characters
from fe10_mod_editor.core.class_parser import parse_all_classes


@pytest.fixture
def char_build_env(backup_dir):
    tmp = tempfile.mkdtemp()
    game_dir = os.path.join(tmp, "Game", "DATA")
    game_files = os.path.join(game_dir, "files")
    shop_out = os.path.join(game_files, "Shop")
    sys_dir = os.path.join(game_dir, "sys")
    os.makedirs(shop_out)
    os.makedirs(sys_dir)
    shutil.copy2(os.path.join(backup_dir, "FE10Data.cms"), game_files)
    for f in ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]:
        shutil.copy2(os.path.join(backup_dir, f), shop_out)
    shutil.copy2(os.path.join(backup_dir, "fst.bin"), sys_dir)
    yield {"tmp": tmp, "backup_dir": backup_dir, "game_dir": game_dir, "game_files": game_files}
    shutil.rmtree(tmp)


def test_character_edit_roundtrip(char_build_env):
    """Build with character edits, verify they apply correctly."""
    # Parse original to find a playable character
    cms_path = os.path.join(char_build_env["backup_dir"], "FE10Data.cms")
    with open(cms_path, "rb") as f:
        orig_data = decompress_lz10(f.read())
    chars = parse_all_characters(orig_data)
    playable = [c for c in chars if c["playability_flag"] != 0]
    target = playable[0]

    proj = ProjectFile.new()
    proj.paths["backup_dir"] = char_build_env["backup_dir"]
    proj.paths["game_dir"] = char_build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(char_build_env["backup_dir"])
    proj.character_edits[target["pid"]] = {
        "growth_rates": {"hp": 99, "str": 88},
        "stat_adjustments": {"hp": 10},
        "level": 20,
    }

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    # Verify edits applied
    output_cms = os.path.join(char_build_env["game_files"], "FE10Data.cms")
    with open(output_cms, "rb") as f:
        modded = decompress_lz10(f.read())
    modded_chars = parse_all_characters(modded)
    modded_target = next(c for c in modded_chars if c["pid"] == target["pid"])

    assert modded_target["growth_rates"]["hp"] == 99
    assert modded_target["growth_rates"]["str"] == 88
    assert modded_target["stat_adjustments"]["hp"] == 10
    assert modded_target["level"] == 20


def test_class_max_stat_preset(char_build_env):
    """Build with max stat preset, verify all classes updated."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = char_build_env["backup_dir"]
    proj.paths["game_dir"] = char_build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(char_build_env["backup_dir"])
    proj.misc["class_changes"] = {"set_all_max_stats": True, "max_stats_preset": 60}

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    output_cms = os.path.join(char_build_env["game_files"], "FE10Data.cms")
    with open(output_cms, "rb") as f:
        modded = decompress_lz10(f.read())
    modded_classes = parse_all_classes(modded)

    for cls in modded_classes:
        assert cls["max_stats"]["hp"] == 80  # 60 + 20
        assert cls["max_stats"]["str"] == 60
```

- [ ] **Step 2: Run all tests**

```bash
cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/ -v --timeout=600 -x
```

Fix any failures.

- [ ] **Step 3: Commit and push**

```bash
git add fe10_mod_editor/
git commit -m "feat: add character integration tests and polish"
git push origin master
```

---

## Summary

| Task | Component | Complexity |
|------|-----------|------------|
| 1 | Character Parser (core) | Medium — variable-length entries |
| 2 | Class Parser (core) | Medium — variable-length with nested arrays |
| 3 | Skill Parser (core) | Low — fixed-size entries + restriction tables |
| 4 | Character Data Model | Low — dataclass + database wrapper |
| 5 | Class + Skill Data Models | Low — two small models |
| 6 | Extend ProjectFile | Low — add fields + serialization |
| 7 | Extend ModBuilder | High — binary editing for 3 new data types |
| 8 | Character Table Widget | Medium — computed stats from 2 databases |
| 9 | Editor Sub-Tab Widgets (4) | High — most UI code, 4 distinct editors |
| 10 | Characters Tab View | Medium — wiring sub-tabs + signals |
| 11 | Wire into Main Window + Misc | Medium — integration + new Misc category |
| 12 | Integration Test + Polish | Medium — end-to-end verification |

Tasks 1-7 are the core/model layer (testable without UI). Tasks 8-11 are the UI layer. Task 12 is integration and polish.
