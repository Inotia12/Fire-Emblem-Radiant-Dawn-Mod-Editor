# FE10 Mod Editor — GUI Design Spec

## Overview

A PySide6 desktop application that transforms the existing Fire Emblem: Radiant Dawn modding scripts into a user-configurable GUI editor. Users can edit individual item stats, customize per-chapter shop inventories, apply batch weapon modifications, and build the mod to game files — all through a project-based workflow that stores edits separately from game data.

## Decisions

| Decision | Choice | Rationale |
|----------|--------|-----------|
| GUI Framework | PySide6 (Qt6) | Best widget set for data tables/editors, LGPL license, mature ecosystem |
| Workflow | Project-based | Edits saved as `.fe10mod` JSON, applied to game files on explicit "Build" |
| Target Audience | Developer-first | Built for the author initially, community polish later |
| PRF Editing | Simple toggle (batch) | Remove/keep PRF locks globally via Misc tab, not per-item |
| Guardrails | Soft warnings | Highlight out-of-range values, never block edits |
| Difficulty Levels | Unified with overrides | Edit once for all difficulties, override specific chapters per-difficulty |
| Backup Policy | Hash-verified, write-once | MD5 hashes stored in project file on first backup, verified every build |

## Application Layout

Tab-based main window with collapsible side panel:

```
┌──────────────────────────────────────────────────────────┐
│ File  Edit  Tools  Help                                  │
├──────────────────────────────────────────────────────────┤
│ [Open Project] [Save]                    my_mod.fe10mod  │
├──────────────────────────────────────────────────────────┤
│ [Items] [Shops] [Build] [Misc]                           │
├────────────────────────────────────┬─────────────────────┤
│                                    │                     │
│  Main content area                 │  Side panel         │
│  (varies by tab)                   │  (contextual)       │
│                                    │                     │
├────────────────────────────────────┴─────────────────────┤
│ 296 items loaded • 0 modified              Backup: C:\…  │
└──────────────────────────────────────────────────────────┘
```

## Tab 1: Items

### Main Area
- Filterable, sortable table of all 296 items
- Columns: Name, Type, Rank, Might, Hit, Critical, Weight, Uses, Price, PRF indicator
- Search bar with text filter
- Weapon type filter chips (All, Swords, Lances, Axes, Bows, Knives, Magic, etc.)
- PRF items highlighted with a gold indicator
- Modified items visually distinguished from unmodified ones

### Side Panel (on item select)
Grouped editable fields:

**Combat Stats:** Might, Accuracy, Critical, Weight, Uses, WExp Gain (all u8, 0-255)

**Economy:** Price (u16, 0-65535) — the raw cost field stored in the item data; the game calculates total purchase cost from this value

**Classification:**
- Weapon Type (read-only display)
- Weapon Rank (dropdown: E, D, C, B, A, S)

**Actions:** "Reset to Original" button to revert all edits on the selected item

### Soft Guardrails
- Fields highlighted yellow when values exceed the vanilla game's observed range for that weapon type
- Tooltip showing original value on hover
- No blocking — user can set any valid value for the data type

## Tab 2: Shops

### Chapter List (Left Sidebar)
- Chapters grouped by Part (1–4) with section headers
- Each entry shows chapter number and name
- Chapters that originally had no shop are grayed out with a "no shop" label
- Selected chapter highlighted with accent border

### Shop Inventory (Main Area)
Two-column layout side by side:

**Weapon Shop (left column):**
- Checkbox list of all 126 weapons
- Checked = in stock for this chapter, unchecked = available to add (shown grayed)
- Counter: "X / 126 weapons stocked"
- Quick actions: "Stock All", "Clear"

**Item Shop (right column):**
- Checkbox list of all 109 consumables/rods
- Same checked/unchecked pattern
- Counter: "X / 109 items stocked"
- Quick actions: "Stock All", "Clear"

### Difficulty Handling
- Difficulty selector in the chapter header: All | Normal | Hard | Maniac
- Default mode is "All" — edits apply to all three difficulties (unified)
- Clicking a specific difficulty creates an override for that chapter on that difficulty
- Bottom bar shows current editing mode: "All Difficulties (unified)" or "Hard (override)"
- Overrides are sparse — only the chapters/difficulties that differ need entries

### Price Display
- Price column in shop tables reflects values from the Items tab (read-only in shops context)
- Prices are a property of the item, not the shop

## Tab 3: Build

### Left Column — Settings & Actions

**Paths:**
- Backup Directory — path to original unmodified game files, with Browse button
- Game Directory — output target for modified files, with Browse button
- Validation indicator showing whether backup files were found and verified

**Change Summary:**
- At-a-glance counts: items modified, shops customized, difficulty overrides, misc toggles active

**Build Mod Button:**
- Runs the full pipeline: decompress FE10Data.cms → apply item edits → apply misc toggles → recompress → rebuild shop files → update fst.bin
- Disabled if backup validation fails

**Danger Zone:**
- "Restore Original Files from Backup" — copies all backup files back to game directory
- Confirmation dialog before executing

### Right Column — Build Log
- Scrolling monospace output
- Color-coded: green (success), yellow (warnings), white (progress)
- Shows each pipeline step with timestamps
- Persists across builds within the session

## Tab 4: Misc

Batch toggle operations organized by category. Each toggle is a card with:
- Toggle name
- Description of what it does
- On/off switch
- Count of affected items

### Category: Weapon Changes

**Remove PRF Locks** — Changes weapon rank from N (personal) to D on all 18 PRF weapons, removes equip-lock attributes (eqA, eqB, etc). Allows any character to equip previously locked weapons.

**Remove Valuable Flag** — Removes the "valuable" attribute from all 34 items that have it. Valuable items cannot be discarded or sold.

**Remove Steal Protection** — Removes the "sealsteal" attribute from all 9 items that have it. Makes all items stealable.

### Extensibility
- Categories are rendered dynamically from a data structure, not hardcoded layout
- New categories and toggles can be added by extending the data model
- Placeholder area shown for future categories (e.g., Character Changes, Difficulty Tweaks)

## Project File Format (`.fe10mod`)

JSON file storing only diffs from original game data:

```json
{
  "version": 1,
  "paths": {
    "backup_dir": "C:\\...\\Backup",
    "game_dir": "C:\\...\\Game\\DATA"
  },
  "backup_hashes": {
    "FE10Data.cms": "a1b2c3...",
    "shopitem_n.bin": "d4e5f6...",
    "shopitem_m.bin": "...",
    "shopitem_h.bin": "...",
    "fst.bin": "..."
  },
  "item_edits": {
    "IID_IRON_SWORD": {
      "price": 0,
      "might": 12
    }
  },
  "shop_edits": {
    "unified": {
      "C0101": {
        "weapons": ["IID_IRON_SWORD", "IID_STEEL_SWORD"],
        "items": ["IID_VULNERARY", "IID_CONCOCTION"]
      }
    },
    "overrides": {
      "hard": {
        "C0101": {
          "weapons": ["IID_IRON_SWORD"]
        }
      }
    }
  },
  "misc": {
    "weapon_changes": {
      "remove_prf_locks": true,
      "remove_valuable": false,
      "remove_seal_steal": false
    }
  }
}
```

### Key Principles
- **Only diffs stored** — items not in `item_edits` keep original values; shops not in `shop_edits` keep original inventory
- **Overrides are sparse** — difficulty overrides only specify chapters that differ from unified
- **Backup hashes computed once** — on first backup creation, stored in project file, verified on every build
- **Version field** — for future format migrations

## Backup Safety

1. **Backups contain only original files** — never overwrite a backup with modified files
2. **MD5 verification** — on first backup setup, compute MD5 hashes of all source files and store them in the project file under `backup_hashes`
3. **Write-once policy** — if the backup directory already contains files with matching hashes, never write to it again
4. **Refuse bad backups** — if the user points at files that don't match stored hashes (already modded), refuse to create a backup and warn the user
5. **Verify before every build** — before any build, re-verify backup files against stored hashes; abort if mismatch detected
6. **Region-scoped** — hashes are per-project; different regions will have different hashes stored in their respective project files

## Data Flow

### Loading a Project
1. Open `.fe10mod` file → parse JSON
2. Verify backup directory exists and files match stored hashes
3. Parse `Backup/FE10Data.cms` (decompress LZ10 → read ItemData section at 0xDF44)
4. Build in-memory item database (296 items with all properties)
5. Parse original shop files to get per-chapter vanilla inventory
6. Apply `item_edits` as overlays on top of original values
7. Apply `shop_edits` as overlays on top of original shop inventories
8. Populate UI

### Building the Mod
1. Verify backup hashes
2. Start from clean backup copies (never from previously modified files)
3. Apply `item_edits` to decompressed FE10Data binary
4. Apply `misc` toggles (PRF removal, valuable removal, seal steal removal)
5. Recompress FE10Data with LZ10, pad to original size
6. Rebuild shop files using CompressShopfile algorithm with edited inventories
7. Update fst.bin with new file sizes
8. Write all output to game directory

## Architecture

```
fe10_mod_editor/
├── main.py                    # Entry point, QApplication setup
├── models/
│   ├── project.py             # Project file load/save, validation
│   ├── item_database.py       # Parse FE10Data, item data model
│   ├── shop_database.py       # Parse shop files, shop data model
│   └── mod_builder.py         # Build pipeline (replaces mod_free_shop.py)
├── views/
│   ├── main_window.py         # Main window, tab bar, status bar
│   ├── items_tab.py           # Items table + side panel
│   ├── shops_tab.py           # Chapter list + shop inventory
│   ├── build_tab.py           # Paths, summary, build button, log
│   └── misc_tab.py            # Batch toggle categories
├── widgets/
│   ├── item_table.py          # Filterable/sortable item table widget
│   ├── item_editor.py         # Side panel editor widget
│   ├── shop_inventory.py      # Checkbox item list with quick actions
│   └── toggle_card.py         # Misc tab toggle card widget
└── core/
    ├── binary_parser.py       # LZ10, CMS format parsing (extracted from existing scripts)
    ├── shop_builder.py        # CompressShopfile algorithm (from rebuild_randomizer_style.py)
    ├── fst_updater.py         # FST patching logic
    └── backup_manager.py      # MD5 verification, backup creation/restore
```

### Separation of Concerns
- **models/** — data parsing, project state, no UI dependencies
- **views/** — PySide6 widgets, layout, user interaction
- **widgets/** — reusable UI components
- **core/** — binary format handling extracted from existing scripts (pure functions, no state)

### Relationship to Existing Code
- `mod_free_shop.py` logic is decomposed into `models/mod_builder.py` (orchestration) and `core/` (format handling)
- `rebuild_randomizer_style.py` becomes `core/shop_builder.py`
- Original scripts can remain in the repo as reference but are no longer the primary entry point

## Binary Format Reference

### Item Entry Layout (in decompressed FE10Data, starting at offset 0xDF44)

The first 4 bytes at 0xDF44 are the item count (296, big-endian u32). Item entries follow immediately at 0xDF48. Each entry has a fixed 56-byte header followed by variable-length trailing data.

**Fixed Header (56 bytes):**

| Offset | Size | Type | Field |
|--------|------|------|-------|
| 0 | 4 | ptr | IID string pointer (item ID, e.g., "IID_IRON_SWORD") |
| 4 | 4 | ptr | MIID string pointer (message/display name ID) |
| 8 | 4 | ptr | MH_I string pointer (help/description message) |
| 12 | 4 | ptr | Display weapon type string pointer |
| 16 | 4 | ptr | Actual weapon type string pointer (used for shop categorization) |
| 20 | 4 | ptr | Weapon rank string pointer ("E", "D", "C", "B", "A", "S", "N") |
| 24 | 4 | ptr | Effect slot 1 pointer |
| 28 | 4 | ptr | Effect slot 2 pointer |
| 32 | 4 | ptr | Effect slot 3 pointer |
| 36 | 1 | u8 | Unknown |
| 37 | 1 | u8 | Icon ID |
| 38 | 2 | u16 | **Price** (big-endian) |
| 40 | 1 | u8 | **Might** (damage) |
| 41 | 1 | u8 | **Accuracy** (hit %) |
| 42 | 1 | u8 | **Critical** chance |
| 43 | 1 | u8 | **Weight** |
| 44 | 1 | u8 | **Uses** (durability) |
| 45 | 1 | u8 | **Weapon EXP gain** |
| 46 | 1 | u8 | Min range (read-only in GUI — not editable) |
| 47 | 1 | u8 | Max range (read-only in GUI — not editable) |
| 48 | 1 | u8 | Unknown flag byte |
| 49-51 | 3 | — | Padding (always 0x000000) |
| 52 | 1 | u8 | Always 0x04 |
| 53 | 1 | u8 | Attribute count (N) |
| 54 | 1 | u8 | Effectiveness count (M) |
| 55 | 1 | u8 | PRF flag (0 or 1) |

**Variable Trailing Data (after byte 55):**

| Section | Size | Description |
|---------|------|-------------|
| Attribute pointers | N × 4 bytes | Pointers to attribute strings ("valuable", "sealsteal", "eqA", etc.) |
| Effectiveness pointers | M × 4 bytes | Pointers to effectiveness-against strings |
| PRF data | 12 bytes if PRF flag=1, 0 otherwise | Character restriction bitmasks / stat bonus values |

**Total entry size** = 56 + (N × 4) + (M × 4) + (PRF_flag × 12)

**Pointer convention:** All string pointers are stored as `actual_file_offset - 0x20` (big-endian u32). Add 0x20 to get the real offset in the decompressed file. A pointer value of 0x00000000 means null/empty.

### CMS Shop File Format

Shop files (shopitem_n/m/h.bin) use a CMS container format:

**Header (40 bytes, starting at offset 0x00):**

| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | Total file size (big-endian u32, stored as value - 0x20) |
| 0x04 | 4 | Data region size (big-endian u32, distance from 0x20 to Pointer Table 1) |
| 0x08 | 4 | Pointer Table 1 entry count (big-endian u32) |
| 0x0C | 4 | Pointer Table 2 entry count (big-endian u32) |
| 0x10-0x27 | 24 | Padding/zeros |

**File Layout (sequential):**

```
0x00      Header (40 bytes)
0x28      Data Region start
            → SHOP_PERSON section (47 entries × 4 raw bytes = 188 bytes)
            → WSHOP_ITEMS sections (per-chapter weapon lists)
            → ISHOP_ITEMS sections (per-chapter consumable lists)
            → FSHOP_ITEMS sections (43 chapters × 720 bytes forge data)
            → FSHOP_CARD section (forge card metadata)
            → String Pool (sorted alphabetically, null-terminated, 4-byte aligned)
          Pointer Table 1 (array of 4-byte offsets into data region where string pointers live)
          Pointer Table 2 / Subsection Table (array of 8-byte entries: data_offset + label_string_offset)
          Label String Pool (null-terminated section label names)
```

**SHOP_PERSON:** 47 entries of 4 raw bytes each. These are NOT string pointers — they are raw flag/configuration bytes. Must be copied verbatim from the original file and never added to the pointer relocation table.

**WSHOP/ISHOP entries:** Per-chapter item lists. Each chapter has a labeled subsection (e.g., `WSHOP_ITEMS_C0101`, `ISHOP_ITEMS_C0101`). Each item entry is 8 bytes: 4-byte IID string pointer + 4 zero bytes. The list is terminated by 4 zero bytes. For ISHOP, the second 4 bytes can contain bargain flags (0x01XX0000 = limited stock).

**Subsection naming convention:** `{TYPE}_ITEMS_{CHAPTER_ID}` where TYPE is WSHOP or ISHOP, and CHAPTER_ID matches the chapter list (C0000, C0101–C0110, C0201–C0204, C0301–C0315, C0401–C0406, C0407a–C0407e, T01–T04).

**String Pool and Pointer Tables:** All strings (IIDs, section labels) are collected into a sorted pool. Pointer Table 1 lists every offset in the data region that contains a string pointer (for runtime relocation). Pointer Table 2 maps section labels to their data offsets (sorted alphabetically by label name).

### Shop-Eligible Item Filtering

Of the 296 items in FE10Data, only 235 are eligible for shops:

**126 Weapon Shop items (WSHOP):** Items whose actual weapon type is one of: sword, lance, axe, bow, knife, flame, thunder, wind, light, dark, card, ballista.

**109 Item Shop items (ISHOP):** All remaining items EXCEPT those excluded by these rules:
- Weapon type is "blow" (unarmed/monster attacks, ~53 items)
- IID starts with `IID_JOG_`, `IID_JUDGE`, `IID_SPRT_HEAL`, `IID_DHEGINHANSEA`, `IID_LEKAIN`, `IID_CEPHERAN` (boss/special weapons)
- Items with "longfar" + "sh" attribute combination (long-range stone attacks)
- Items with "stone" attribute (laguz stone items)

**Items tab shows all 296 items** (including non-shoppable ones) for stat editing purposes. Non-shoppable items are marked as such and do not appear in the Shops tab inventory lists.

### FSHOP and FSHOP_CARD (Out of Scope)

FSHOP (forge shop) data consists of 43 chapters × 720 bytes each, containing forge material/result templates. FSHOP_CARD contains forge card metadata. Both are **passed through unchanged from backup files** during the build pipeline. Forge shop editing is out of scope for v1.

## Difficulty Override Resolution

When building shop files for a specific difficulty:

1. Start with the **original vanilla inventory** for each chapter
2. If the chapter has a **unified edit** in `shop_edits.unified`, it **completely replaces** the vanilla inventory for that chapter
3. If the chapter also has a **difficulty override** in `shop_edits.overrides.{difficulty}`, the override replaces the unified edit **per shop type** (weapons/items independently):
   - If the override specifies `"weapons"`, it replaces the weapons list; otherwise weapons inherit from unified
   - If the override specifies `"items"`, it replaces the items list; otherwise items inherit from unified

Example: If unified C0101 has 50 weapons and 30 items, and a hard override specifies only `"weapons": [10 items]`, then hard C0101 gets 10 weapons + 30 items (items inherited from unified).

## Build Threading

The build pipeline (LZ10 compression in particular) can take several seconds to minutes. To prevent the GUI from freezing:

- The entire build pipeline runs in a **QThread worker**, not on the main UI thread
- Progress is reported via Qt signals to the build log widget
- The Build button is disabled during a build
- The user can observe real-time log output while the build proceeds

## Display Name Resolution

Item display names are resolved from the FE10Data binary:
- The IID string pointer (offset +0) gives the internal ID (e.g., "IID_IRON_SWORD")
- The MIID string pointer (offset +4) gives the message/display name ID
- The actual weapon type pointer (offset +16) provides type classification for filtering and shop categorization

The Items tab "Name" column shows a cleaned-up version of the IID (strip "IID_" prefix, replace underscores with spaces, title case). The full IID is shown in the side panel subtitle. Type classification uses the actual weapon type string to sort items into filter categories.

## Chapter List

The Shops tab chapter list includes all 47 entries from SHOP_PERSON:

**43 game chapters:** C0000 (Prologue), C0101–C0110 (Part 1), C0201–C0204 (Part 2), C0301–C0315 (Part 3), C0401–C0406 + C0407a–C0407e (Part 4)

**4 tutorial chapters:** T01, T02, T03, T04 — grouped under a "Tutorials" section header at the bottom of the list

Chapters that had no shop in vanilla are shown grayed out with a "no shop" label but can still have items added to them.

## Minimum Window Size

Minimum dimensions: **1200×800 pixels**. The item table supports horizontal scrolling if the window is narrower than ideal. The side panel can be collapsed to give more room to the main content area.

## Future Considerations

- **Undo/redo** — Qt's QUndoStack can be integrated for edit history (v2)
- **Per-item PRF character picker** — map PRF bitmask values to character names (v2)
- **Forge shop editing** — expose FSHOP data in the Shops tab (v2)
- **Multi-region support** — validate and handle different game regions
- **Mod presets** — save/load commonly used configurations
