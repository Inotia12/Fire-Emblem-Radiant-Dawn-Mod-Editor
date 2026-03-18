# FE10 Mod Editor — Characters Tab Design Spec

## Overview

A new Characters tab for the FE10 Mod Editor that allows editing allied character data: base stats, growth rates, equipped skills, biorhythm type, laguz transform data, and class max stats. The tab uses a table + tabbed side panel layout, following the existing Items tab pattern with sub-tabs for organizing the larger set of editable fields.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Layout | Table + tabbed side panel | Consistent with Items tab, sub-tabs handle the volume of fields |
| Stat display | Computed final + raw adjustment | Users see game values, modders see what's in the binary |
| Filtering | Allied by default, toggle for all 461 | Focus on playable characters, option to explore everything |
| Skill editing | Equipped list with add/remove | Simple and direct, matches soft-guardrail philosophy |
| Skill warnings | Yellow warning for class-restricted | Skills have prerequisite/blacklist tables; warn but don't block |
| Biorhythm | Type dropdown only | Wave parameter editing deferred to Misc tab future work |
| Max stats | Editable per-class with warning | Affects all characters of that class; user needs to know |
| Max stat batch | Misc toggle, suppresses but preserves individual edits | Non-destructive override |
| Class data | Read-only display | Class editing is a separate future concern |

## Tab Placement

The Characters tab sits between Shops and Misc: **Files | Items | Shops | Characters | Misc**

## Characters Tab Layout

```
┌─────────────────────────────────────┬──────────────────────────┐
│ [Search...] [Filter: Allied ▼]      │ Ike (PID_IKE)            │
│                                     │ Hero | Level 11          │
│ Name     Class      Lv  HP  Str ... │ ┌──────┬────────┬──────┐ │
│ ─────────────────────────────────── │ │Stats │Growths │Skills│ │
│ Ike      Hero       11  44  24  ... │ ├──────┴────────┴──────┤ │
│ Micaiah  Light Mage  1  15   2  ... │ │                      │ │
│ Sothe    Rogue       1  35  18  ... │ │ (sub-tab content)    │ │
│ Edward   Myrmidon    4  19   7  ... │ │                      │ │
│ ...                                 │ │                      │ │
│                                     │ ├──────────────────────┤ │
│ 73 allied characters                │ │ [Reset to Original]  │ │
└─────────────────────────────────────┴──────────────────────────┘
```

### Main Table

- Columns: Name, Class, Level, HP, Str, Mag, Skl, Spd, Lck, Def, Res
- Stats shown are **computed final values** (class base + character adjustment)
- Sortable by any column
- Searchable by name or PID
- Modified characters visually distinguished (bold or highlight)

### Filter Options

- **Allied** (default) — ~73 playable characters
- **All** — all 461 PersonData entries
- **Laguz** — only laguz characters
- **Beorc** — only beorc (human) characters

### Side Panel Header

- Character display name (bold)
- PID subtitle (e.g., PID_IKE)
- Class name + Level as secondary info

### Side Panel Sub-Tabs

4 sub-tabs: **Stats** | **Growths** | **Skills** | **Info**

## Sub-Tab 1: Stats

Shows the 10 character stat fields plus level and authority:

| Stat | Final (read-only) | Adjustment (editable) | Class Base (reference) |
|------|-------------------|----------------------|----------------------|
| HP | 44 | [+6] | 38 |
| Str | 24 | [+2] | 22 |
| Mag | 2 | [-1] | 3 |
| Skl | 28 | [+3] | 25 |
| Spd | 23 | [+1] | 22 |
| Lck | 14 | [+4] | 10 |
| Def | 21 | [+1] | 20 |
| Res | 7 | [-3] | 10 |
| Con | 11 | [+0] | 11 |
| Mov | 7 | [+0] | 7 |

- **Final** = class base + adjustment (computed, read-only display)
- **Adjustment** = editable QSpinBox (-128 to +127, signed byte, stored in binary)
- **Class Base** = gray reference text from JobData
- Editing the adjustment recalculates the final value in real time
- Soft guardrail: yellow highlight if final stat exceeds the class max stat

Additional fields:
- **Level**: QSpinBox (1-40, u8)
- **Authority Stars**: QSpinBox (0-5, u8)

## Sub-Tab 2: Growths

8 growth rate fields as percentages:

| Stat | Growth Rate |
|------|------------|
| HP | [65] % |
| Str | [55] % |
| Mag | [10] % |
| Skl | [60] % |
| Spd | [35] % |
| Lck | [30] % |
| Def | [40] % |
| Res | [15] % |

- Each is QSpinBox (0-255, unsigned byte)
- Soft guardrail: yellow highlight if value exceeds 100%
- Subtitle/tooltip per field shows class growth rate for reference (e.g., "Class growth: +20%")
- Total effective growth = character growth + class growth (shown as reference, not editable here)

## Sub-Tab 3: Skills

Equipped skill list with capacity tracking:

```
Capacity: 12 / 20 used

Equipped Skills:
┌────────────────────────┬──────┬───────┐
│ Skill                  │ Cost │       │
│ Aether                 │  10  │ [ ✕ ] │
│ Shove                  │   5  │ [ ✕ ] │
│ [+ Add Skill ▼]        │      │       │
└────────────────────────┴──────┴───────┘

8 capacity remaining
```

- Each equipped skill shows name and capacity cost
- Remove button (✕) to unequip a skill
- "Add Skill" searchable QComboBox listing all 142 skills
- Running capacity counter: `used / total` (total from class's skill capacity)
- Soft guardrail: capacity counter turns yellow if over limit, does not block
- **Class restriction warnings**: skills with prerequisite/blacklist tables are checked against the character's class. Warning icon + yellow text: "This skill is not normally available to [Class] class" if there's a mismatch. Equipping is still allowed.

### Skill Restriction Data

SkillData entries contain two restriction tables stored separately in the binary:
- **Restriction Table 1** (count at SkillData offset 32, pointer at offset 34): Entries with flag 0x0 are whitelist/prerequisites — only these classes/characters CAN use the skill
- **Restriction Table 2** (count at SkillData offset 33, pointer at offset 38): Entries with flag 0x1 are blacklist/antirequisites — these classes/characters CANNOT use the skill

Each table entry is 8 bytes: 1 flag byte, 3 null bytes, 4-byte ID pointer (to a JID/PID/SID string).

When adding a skill, check the character's JID against both tables:
1. If Table 1 has entries and the character's class is NOT in it → show warning
2. If Table 2 has entries and the character's class IS in it → show warning
Equipping is still allowed (soft guardrail).

## Sub-Tab 4: Info

Read-only class info, editable biorhythm, and laguz data:

**Character:**
- PID (read-only)
- Gender (read-only)

**Class (read-only):**
- Class name
- Movement
- Skill Capacity
- Weapon Ranks (starting)

**Max Stats (editable — class-level):**
- 8 QSpinBox fields: HP, Str, Mag, Skl, Spd, Lck, Def, Res
- Range: 0-255 (unsigned bytes in binary, displayed as-is)
- Warning label: "Editing max stats affects all [Class Name] characters"
- If the Misc "Set All Max Stats" toggle is active, these fields are disabled with a note: "Overridden by Misc > Class Changes > Set All Max Stats"

**Biorhythm:**
- Type: QComboBox with the following options:

| Byte Value | Label | Description |
|-----------|-------|-------------|
| 0 | Best | Strongest biorhythm cycle |
| 1 | Good | Above average cycle |
| 2 | Average | Standard cycle |
| 3 | Bad | Below average cycle |
| 4 | Worst | Weakest cycle |
| 5-9 | Type 5-9 | Additional types (rare, used by specific characters) |
| 0xFF | None | No biorhythm (shown as "None" in dropdown) |

The 5 BioData entries at 0x27608 define the wave parameters for types 0-4. Types 5-9 map to the same 5 entries cyclically (type % 5). 0xFF disables biorhythm entirely.

**Laguz Data (only visible for Laguz characters):**
- Gauge gain per turn: QSpinBox (signed byte)
- Gauge gain per battle: QSpinBox (signed byte)
- Gauge loss per turn: QSpinBox (signed byte)
- Gauge loss per battle: QSpinBox (signed byte)

## Misc Tab Addition: Class Changes Category

New category added to the Misc tab, below "Weapon Changes":

### Category: Class Changes

**Set All Max Stats** — Sets all class max stat caps to a preset value. HP gets +20 over the base preset.

- Toggle on/off switch
- Preset selector: QComboBox with [40, 60, 80, Custom]
- Custom mode: QSpinBox for the base value (HP = base + 20)
- When enabled: overrides individual max stat edits from the Characters tab (edits are preserved in the project file but suppressed during build)
- Affects 171 classes
- Description: "Sets every class's max stats to the selected value (+20 for HP). Individual max stat edits are preserved but suppressed while this is active."

## Binary Format Reference

### PersonData (Character Entries)

461 entries starting at offset **0x2C** in decompressed FE10Data. The first 4 bytes at 0x2C are the entry count (461, u32 BE). Entries begin at 0x30. Variable-length entries.

**Note on section counts:** Like ItemData, PersonData, JobData, and SkillData each begin with a 4-byte count field (u32 BE) followed by the entries. The parser should read this count rather than hardcoding it.

**Entry structure:**

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 1 | u8 | Skill count (N) |
| 1 | 1 | u8 | Null |
| 2 | 1 | u8 | Starting level |
| 3 | 1 | u8 | Gender (0=male, 1=female) |
| 4 | 4 | ptr | PID string pointer (person ID) |
| 8 | 4 | ptr | MPID string pointer (display name) |
| 12 | 4 | ptr | MNPID string pointer (description) |
| 16 | 4 | ptr | FID string pointer (face ID) |
| 20 | 4 | ptr | JID string pointer (class/job ID) |
| 24 | 4 | ptr | Affinity string pointer |
| 28 | 4 | ptr | Starting weapon ranks pointer |
| 32 | N×4 | ptrs | Skill ID pointers (one per equipped skill) |
| 32+N×4 | 4 | — | Null padding |
| 36+N×4 | 16 | ptrs | 4 animation/action ID pointers |
| 52+N×4 | 1 | u8 | Biorhythm type (0x00-0x09, 0xFF=none) |
| 53+N×4 | 1 | u8 | Unknown flag |
| 54+N×4 | 1 | u8 | Unknown flag |
| 55+N×4 | 1 | u8 | Playability flag (0x00/0x03/0x07/0x0F/0x1F for playable) |
| 56+N×4 | 1 | u8 | Authority stars |
| 57+N×4 | 4 | i8×4 | Laguz transform modifiers (gain/turn, gain/battle, loss/turn, loss/battle) |
| 61+N×4 | 10 | i8×10 | Stat adjustments (HP, Str, Mag, Skl, Spd, Lck, Def, Res, Con, Mov) |
| 71+N×4 | 8 | u8×8 | Growth rates (HP, Str, Mag, Skl, Spd, Lck, Def, Res) |

**Total entry size** = 79 + (N × 4) bytes

**Pointer convention:** Same as ItemData — stored as `actual_offset - 0x20`.

**Identifying allied characters:** Use the playability flag byte at offset 55+N×4. Non-zero values (0x03, 0x07, 0x0F, 0x1F) indicate playable characters. Value 0x00 indicates non-playable (enemy/NPC). This is the canonical method — no hardcoded PID list needed.

**Identifying Laguz vs Beorc:** Determined by the character's class. If the JID resolves to a laguz class (class names containing "wolf", "tiger", "cat", "lion", "hawk", "raven", "heron", "dragon", or classes with laguz-specific mount types in JobData), the character is Laguz. The simplest implementation: check if any of the 4 laguz transform modifier bytes (offset 57+N×4) are non-zero — Laguz characters have non-zero gauge values, Beorc have all zeros.

**Con and Mov:** These two stats have character adjustments (in the 10-byte stat adjustment block) but do NOT have growth rates or max stat caps. They appear in the Stats sub-tab but not in Growths or Max Stats. This is correct game behavior, not an omission.

### JobData (Class Entries)

171 entries starting at offset **0x926C**. The first 4 bytes at 0x926C are the entry count (171, u32 BE). Entries begin at 0x9270. Variable-length entries.

**Entry structure:**

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 4 | ptr | JID string pointer (class ID) |
| 4 | 4 | ptr | MJID string pointer (display name) |
| 8 | 4 | ptr | Japanese name pointer |
| 12 | 4 | ptr | MH_J help pointer |
| 16 | 4 | ptr | Promotes-from class pointer |
| 20 | 4 | ptr | Promotes-to class pointer |
| 24 | 4 | ptr | Alternate job pointer |
| 28 | 4 | ptr | Attack item pointer |
| 32 | 4 | ptr | Animation ID pointer |
| 36 | 4 | ptr | Base weapon ranks pointer |
| 40 | 4 | ptr | Max weapon ranks pointer |
| 44 | 1 | u8 | Constitution |
| 45 | 1 | u8 | Armor type |
| 46 | 1 | u8 | Armor weight |
| 47 | 1 | u8 | Mount type |
| 48 | 1 | u8 | Mount weight |
| 49 | 1 | u8 | Skill count (M) |
| 50 | 1 | u8 | SFXC/attribute count (S) |
| 51 | 1 | u8 | Promote level |
| 52 | 1 | u8 | Movement type |
| 53 | 1 | u8 | **Default movement** |
| 54 | 1 | u8 | **Skill capacity** |
| 55 | 1 | u8 | Vision range |
| 56 | M×4 | ptrs | Skill ID pointers (class default skills) |
| 56+M×4 | 4 | ptr | Satori Sign skill pointer |
| 60+M×4 | S×4 | ptrs | Attribute/SFXC pointers |
| 60+M×4+S×4 | 8 | u8×8 | **Max stats** (HP, Str, Mag, Skl, Spd, Lck, Def, Res) |
| +8 | 8 | i8×8 | **Base stats** (HP, Str, Mag, Skl, Spd, Lck, Def, Res) |
| +16 | 8 | u8×8 | **Class growth rates** (HP, Str, Mag, Skl, Spd, Lck, Def, Res) |
| +24 | 8 | i8×8 | Promotion stat adjustments (null if unpromoted class) |

**Total entry size** = 92 + (M × 4) + (S × 4) bytes

**Max stats encoding:** Unsigned bytes (u8, range 0-255). Values represent the stat cap for that class (e.g., 30 Str max = byte value 30). The "Set All Max Stats" preset writes the chosen value directly.

### SkillData

142 entries starting at offset **0x12810**. Each entry is 0x2C (44) bytes.

**Key fields:**

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 4 | ptr | SID string pointer (skill ID) |
| 4 | 4 | ptr | MSID string pointer (display name) |
| 8 | 4 | ptr | MH_SKILL pointer (help text) |
| 12 | 4 | ptr | MH2_SKILL pointer (extended help) |
| 16 | 4 | ptr | Effect 1 pointer |
| 20 | 4 | ptr | Effect 2 pointer |
| 24 | 4 | ptr | Associated item pointer |
| 28 | 1 | i8 | Counter value |
| 29 | 1 | u8 | Visibility (1=visible, 2=grayed, 3=hidden) |
| 30 | 1 | i8 | **Capacity cost** |
| 31 | 1 | u8 | Unknown |
| 32 | 1 | u8 | Restriction table 1 count |
| 33 | 1 | u8 | Restriction table 2 count |
| 34 | 4 | ptr | Restriction table 1 pointer |
| 38 | 4 | ptr | Restriction table 2 pointer |

**Restriction table entries** (8 bytes each):
- Byte 0: Flag (0x0 = whitelist/prerequisite, 0x1 = blacklist/antirequisite)
- Bytes 1-3: Null
- Bytes 4-7: ID pointer (to skill/person/job/attribute string)

### BioData (Biorhythm Types)

5 entries at offset **0x27608**, 12 bytes each. Each defines the sine wave parameters for a biorhythm pattern. The character entry stores a type index (0-4) referencing these entries.

## Project File Additions

New fields in the `.fe10mod` JSON:

```json
{
  "character_edits": {
    "PID_IKE": {
      "level": 11,
      "authority_stars": 2,
      "stat_adjustments": { "hp": 6, "str": 5, "mag": -1 },
      "growth_rates": { "hp": 70, "str": 60 },
      "biorhythm_type": 2,
      "skills": ["SID_AETHER", "SID_SHOVE"],
      "laguz_gauge": { "gain_turn": 5, "gain_battle": 8, "loss_turn": -3, "loss_battle": -5 }
    }
  },
  "class_max_stat_edits": {
    "JID_HERO": { "hp": 60, "str": 30, "mag": 26, "skl": 30, "spd": 28, "lck": 30, "def": 27, "res": 22 }
  },
  "misc": {
    "weapon_changes": { ... },
    "class_changes": {
      "set_all_max_stats": false,
      "max_stats_preset": 40
    }
  }
}
```

**Only diffs stored** — character fields not in `character_edits` keep original values. Class max stats not in `class_max_stat_edits` keep original values.

## Binary Editing Strategy: Skill Count Changes

Editing a character's equipped skills can change the skill count N, which changes the total entry size (79 + N×4 bytes). Since PersonData entries are packed sequentially, changing one entry's size would shift every subsequent entry.

**Strategy: Skill replacement only (v1).** The editor allows replacing existing skill pointers and nulling them out (unequip), but does NOT allow increasing the skill count beyond the original. To "add" a skill, the user replaces a null slot or an existing skill. If a character has 2 equipped skills and 0 null slots, the user must remove one before adding a different one.

This avoids the complexity of rebuilding the entire PersonData section. The build pipeline patches skill pointer values in-place at their known offsets without changing entry sizes.

**Future (v2):** Full skill count editing would require rebuilding PersonData from scratch (similar to how shop files are rebuilt). This is deferred.

**Implementation detail:** When parsing characters, record the original skill count N and the byte offset of each skill pointer slot. During build, write skill SID pointers into those same slots. Unequipped slots get a null pointer (0x00000000). The skill count byte at offset 0 of the entry is NOT modified.

## Data Flow

### Display Name Resolution

Character display names come from resolving the MPID string pointer (offset +8 in the entry). If MPID resolves to a message ID string (e.g., "MPID_IKE"), the display name is derived from the PID instead: strip "PID_" prefix, replace underscores, title case (same approach as item IIDs). The full PID is shown in the side panel subtitle.

### Loading Characters

1. Decompress FE10Data.cms once — reuse the same decompressed buffer for all parsers (items, characters, classes, skills)
2. Parse PersonData section (count + entries at 0x2C)
3. Parse JobData section (count + entries at 0x926C) — needed for class base stats, max stats, skill capacity
4. Parse SkillData section (count + entries at 0x12810) — needed for skill names, costs, restrictions
5. Build in-memory CharacterDatabase, ClassDatabase, and SkillDatabase
6. Apply `character_edits` and `class_max_stat_edits` as overlays
7. Populate UI

### Building Characters (in ModBuilder)

1. Start from clean backup decompressed FE10Data
2. Apply `character_edits`: write stat adjustments, growth rates, level, authority, biorhythm, skill pointers
3. Apply `class_max_stat_edits`: write max stat bytes in JobData entries
4. Apply `misc.class_changes.set_all_max_stats`: if enabled, overwrite ALL class max stats with preset value (HP = preset + 20)
5. Recompress and write (existing pipeline)

## Architecture

New files to create:

```
fe10_mod_editor/
├── core/
│   ├── character_parser.py    # Parse PersonData section from decompressed FE10Data
│   ├── class_parser.py        # Parse JobData section
│   └── skill_parser.py        # Parse SkillData section
├── models/
│   ├── character_data.py      # CharacterEntry dataclass, CharacterDatabase
│   ├── class_data.py          # ClassEntry dataclass, ClassDatabase
│   └── skill_data.py          # SkillEntry dataclass, SkillDatabase
├── views/
│   └── characters_tab.py      # Characters tab view with sub-tabbed side panel
├── widgets/
│   ├── character_table.py     # Character table widget (like item_table.py)
│   ├── character_stats_editor.py   # Stats sub-tab widget
│   ├── character_growths_editor.py # Growths sub-tab widget
│   ├── character_skills_editor.py  # Skills sub-tab widget
│   └── character_info_editor.py    # Info sub-tab widget
```

Files to modify:
- `views/main_window.py` — add Characters tab, load character/class/skill data
- `views/misc_tab.py` — add Class Changes category
- `models/mod_builder.py` — apply character edits, class max stat edits, max stat preset during build
- `models/project.py` — add character_edits, class_max_stat_edits, misc.class_changes fields
