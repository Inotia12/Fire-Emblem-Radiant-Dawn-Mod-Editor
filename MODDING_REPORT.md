# Fire Emblem: Radiant Dawn - Free All-Items Shop Mod

## Final Project Structure
```
Project Root/
├── Game/                           # Game disc (extracted with wit)
│   ├── DATA/
│   │   ├── files/
│   │   │   ├── FE10Data.cms              # Modified: prices, attrs, ranks
│   │   │   ├── FE10Data_decompressed.bin # Intermediate (generated)
│   │   │   └── Shop/
│   │   │       ├── shopitem_n.bin        # Rebuilt: all items every chapter
│   │   │       ├── shopitem_m.bin        # Rebuilt: all items every chapter
│   │   │       └── shopitem_h.bin        # Rebuilt: all items every chapter
│   │   └── sys/
│   │       └── fst.bin                   # Updated: new shop file sizes
│   └── UPDATE/
├── Backup/                         # Original unmodified files
│   ├── FE10Data.cms
│   ├── fst.bin
│   ├── shopitem_n.bin
│   ├── shopitem_m.bin
│   └── shopitem_h.bin
├── mod_free_shop.py                # Main mod script (runs everything)
├── rebuild_randomizer_style.py     # Shop file rebuilder (called by mod script)
├── MODDING_REPORT.md               # This document
└── item_database_output.txt        # Reference: all 296 items with stats
```

## How to Apply the Mod

```bash
# 1. Extract game disc with wit
wit EXTRACT game.iso Game/

# 2. Copy originals to Backup/
mkdir Backup
cp Game/DATA/files/FE10Data.cms Backup/
cp Game/DATA/files/Shop/shopitem_*.bin Backup/
cp Game/DATA/sys/fst.bin Backup/

# 3. Run the mod
python mod_free_shop.py

# 4. Rebuild ISO
wit COPY Game/ "Fire Emblem Radiant Dawn (Modded).iso"
```

## How to Undo
Copy all files from `Backup/` back to their original locations in `Game/`.

## CMS File Format (CRITICAL)

CMS is the binary container format used throughout Radiant Dawn. All multi-byte integers are big-endian.

### Header (16 bytes at 0x00-0x0F)
| Offset | Size | Field |
|--------|------|-------|
| 0x00 | 4 | Total file size |
| 0x04 | 4 | Data region size (distance from byte 0x20 to Pointer Table 1 start) |
| 0x08 | 4 | Pointer Table 1 entry count |
| 0x0C | 4 | Pointer Table 2 entry count (subsection count) |

Bytes 0x10-0x27 are padding/zeros. Some files have a date string pointer at 0x20 and author pointer at 0x24, but these are technically part of the data region.

### The -0x20 Convention (CRITICAL)
ALL pointer values in CMS files use an offset relative to byte 0x20 (the data region start):
- String pointer in data: `actual_file_offset = stored_value + 0x20`
- Pointer Table 1 entries: `file_offset_of_pointer = entry_value + 0x20`
- Subsection data_ptr: `file_offset_of_data = data_ptr + 0x20`
- Header data_region_size: `pointer_table_1_file_offset = data_region_size + 0x20`

### File Layout (in order)
1. Header (0x00-0x0F, 16 bytes used, rest zero-padded to 0x28)
2. Data Region (starts at 0x28): SHOP_PERSON, WSHOP, ISHOP, FSHOP, FSHOP_CARD, then string pool
3. Pointer Table 1: sorted list of data-region offsets where string pointers exist
4. Pointer Table 2 (Subsection Table): 8-byte entries (data_offset + label_string_offset), sorted alphabetically by label
5. Label String Pool: null-terminated ASCII label names

### Pointer Table 1
Each entry is 4 bytes (big-endian): the offset (relative to byte 0x20) of a location in the data region that contains a string pointer. These tell the game engine which data locations need pointer relocation when the file is loaded into memory.

### Pointer Table 2 (Subsection Table)
177 entries (for shop files), each 8 bytes:
- 4 bytes: data offset (relative to byte 0x20) pointing to where the section's data begins
- 4 bytes: label string offset (relative to the start of the label string pool)

Entries are sorted ALPHABETICALLY by label name:
| Entries | Section |
|---------|---------|
| 0 | FSHOP_CARD_DATA |
| 1-43 | FSHOP_ITEMS_C0000 through C0407e |
| 44-86 | ISHOP_ITEMS_C0000 through C0407e |
| 87-133 | SHOP_PERSON_C0000 through C0407e, T01-T04 |
| 134-176 | WSHOP_ITEMS_C0000 through C0407e |

## Shop Data Sections

### SHOP_PERSON
47 entries of 4 raw bytes each. These are NOT string pointers - they are raw flag/configuration bytes controlling shop availability. Values like 0x01020304, 0x05050500, 0x06060600. Must be preserved verbatim - do NOT add to pointer table.

### WSHOP_ITEMS (Weapon Shop)
Per-chapter weapon lists. Each item is 8 bytes:
- 4-byte IID string pointer (relative to byte 0x20)
- 4 bytes: zeros (no bargain flags for weapons)
- Terminated by 4 zero bytes (NULL terminator)

### ISHOP_ITEMS (Item Shop)
Same format as WSHOP. The second 4-byte field can contain bargain flags:
- 0x00000000 = regular stock (unlimited)
- 0x01XX0000 = bargain item (limited stock)

### FSHOP_ITEMS (Forge Shop)
43 entries of exactly 720 bytes each (180 dwords). Contains forge templates with MIK_, MDV_, and IID_ string pointers.

### FSHOP_CARD (Forge Card Metadata)
Contains MESS_ string pointers mixed with numeric configuration data. When rebuilding, must identify which dwords are string pointers (resolve to known strings) vs raw data (preserve as-is).

## Item Modifications in FE10Data.cms

The mod applies 5 types of changes to item data:

### 1. All prices set to 0 (284 items)
The 2-byte `cost_per_use` field at entry offset +38 is zeroed for all 296 items (284 had non-zero prices). This makes every item free in shops.

### 2. `sealsteal` attribute removed (9 items)
This attribute prevents items from being traded or stolen. Removed from: IID_RAGNELL, IID_AMITE, IID_FIRETAIL, IID_THUNDERTAIL, IID_WINDTAIL, IID_ELSILENCE, IID_ELSLEEP, IID_REWARP, IID_RUDOLGEM.

### 3. `valuable` attribute removed (34 items)
This attribute prevents items from being discarded or sold. Removed from all legendary weapons, promotion items, boss weapons, and special items.

### 4. `eq*` equip restriction attributes removed (11 items)
These attributes (eqA through eqI) lock weapons to specific characters or character classes. Each maps to a unique character:
- eqA = Ike (Ragnell, Alondite)
- eqB = Elincia (Florete, Holy Crown)
- eqC = Elincia/Geoffrey (Amiti)
- eqD = Micaiah (Thany)
- eqE = Sanaki (Cymbeline)
- eqF = Lehran (Creiddyled)
- eqG = Edward (Caladborg)
- eqH = Shinon (Lughnasad)
- eqI = Nolan (Tarvos)

With eq* removed, any character with the right weapon type and rank can equip these weapons.

### 5. Rank N changed to rank D (18 items)
Weapons with rank "N" (meaning "personal weapon, no standard rank") cannot be equipped by characters who don't have the PRF permission. Changing to rank "D" means any character with at least D-rank proficiency in the weapon type can equip it. This works together with the eq* removal - rank N->D removes the rank barrier, and eq* removal removes the character barrier.

Items changed: IID_CALADBORG, IID_RAGNELL, IID_AMITE, IID_TARVOS, IID_LUGHNASAD, IID_FLORETE, IID_ALONDITE, IID_BOWGUN, IID_CROSSBOW, IID_TAKHSH, IID_AQQAR, IID_ARBALEST, IID_CYMBELINE, IID_THANY, IID_CREIDDYLED, IID_SPRT_HEAL, IID_SPRT_HEAL_SP, IID_FLUTTER.

### Important: PRF bitmask data must NOT be modified
The 12-byte PRF data (3 dwords at the end of PRF-flagged entries) serves DUAL purposes depending on item type:
- For **weapons**: encodes character restriction bitmasks
- For **stat boosters**: encodes WHICH STAT to boost and BY HOW MUCH (e.g., Angel Robe = 0x07 in first byte = +7 HP)
- For **staves**: encodes staff-specific parameters

Setting PRF data to 0xFFFFFFFF breaks stat boosters (turns +7 HP into -1 to all stats). Setting to 0x00000000 breaks them too (no stat boost). The PRF bitmask data must be preserved as-is. Instead, use the rank N->D and eq* removal approach to unlock weapons.

### FE10Data.cms Technical Details

#### Compression
LZ10 compressed. First byte = 0x10, bytes 1-3 = decompressed size (little-endian, 3 bytes).
After modifying and recompressed, PAD to the original file size with zero bytes to avoid issues.

#### ItemData Section
- Count stored as big-endian u32 at offset 0xDF44 in decompressed data = 296
- Entry data starts at 0xDF48
- Each entry is variable length: `56 + (attr_count * 4) + (eff_count * 4) + (prf_flag * 12)`
  - attr_count at entry offset +53
  - eff_count at entry offset +54
  - prf_flag at entry offset +55
- Cost per use field: 2-byte big-endian u16 at entry offset +38
- Total price = cost_per_use x uses (uses at offset +44)
- Set cost_per_use to 0x0000 for free items

### Item Categories (296 total)
- 126 items suitable for WSHOP (weapons): sword, lance, axe, bow, knife, flame, thunder, wind, light, dark, card, ballista types
- 109 items suitable for ISHOP (items/consumables): rod, item types
- 61 excluded: laguz strikes (blow attribute), fixed ballistae (longfar+sh), spirit/boss weapons (IID_JOG_*, IID_JUDGE, IID_SPRT_HEAL*, IID_DHEGINHANSEA*, IID_LEKAIN*, IID_CEPHERAN*), Onager (stone attribute)

## FST (File System Table)
Located at `Game/DATA/sys/fst.bin`. Contains file sizes for every file on disc. MUST be updated when shop file sizes change.

Shop file FST entry indices (found by searching):
- shopitem_h.bin: entry 1788
- shopitem_m.bin: entry 1789
- shopitem_n.bin: entry 1790
- FE10Data.cms: entry 674

Each FST entry is 12 bytes. The size field is at bytes 8-11 (big-endian u32).

## Rebuild Algorithm (Proven Working - matches fe10-randomizer)

The shop files MUST be rebuilt from scratch following this exact algorithm (based on the fe10-randomizer's CompressShopfile method). Patching the original files in-place can cause crashes due to subtle structural dependencies.

1. Write 40 zero bytes as placeholder header
2. Write data sections in order: SHOP_PERSON (raw bytes), WSHOP (all chapters), ISHOP (all chapters), FSHOP (preserved from original), FSHOP_CARD (preserved, string pointers remapped)
3. Write string pool: all unique strings sorted ALPHABETICALLY, null-terminated, 4-byte aligned
4. Write Pointer Table 1: all data-region offsets where string pointers exist (relative to byte 0x20)
5. Write Pointer Table 2: subsection entries sorted ALPHABETICALLY by label
6. Write label strings
7. Back-fill all string pointer values in data region (resolve to string pool offsets relative to byte 0x20)
8. Write final header at offset 0x00: file_size, data_region_size, PT1_count, PT2_count

## Lessons Learned / Pitfalls

### 1. Corrupted file extraction breaks everything
The original issue that caused Part 1 crashes was a corrupted zip extraction tool. Always verify clean extraction by rebuilding the ISO and confirming it loads.

### 2. Never patch shop files in-place
Even single-byte changes to the original shop file binary can cause crashes. The file must be rebuilt from scratch using the full CompressShopfile algorithm. The fe10-randomizer project (github.com/LordMewtwo73/fe10-randomizer) documents this approach.

### 3. SHOP_PERSON data is raw bytes, not pointers
The SHOP_PERSON data at the start of the data region (0x28+) looks like it could be pointers (values like 0x01020304) but these are raw configuration flags. Adding them to the pointer relocation table corrupts the file.

### 4. The -0x20 convention applies everywhere
Every pointer-like value in the CMS format is stored as `actual_offset - 0x20`. This includes the header's data_region_size field, all Pointer Table 1 entries, all Pointer Table 2 data offsets, and all string pointers in the data region.

### 5. FST must be updated
When shop file sizes change, the FST must be updated with correct sizes. Mismatched sizes can cause file loading failures.

### 6. Pad recompressed LZ10 to original size
After recompressing FE10Data.cms, pad with zeros to match the original file size. Size mismatches can cause decompression issues.

### 7. The randomizer never touches shopitem_n.bin
The fe10-randomizer only modifies shopitem_h.bin and shopitem_m.bin, never shopitem_n.bin. Our mod modifies all three for complete coverage.

### 8. String pool must be sorted alphabetically
The randomizer sorts all strings alphabetically when rebuilding. Following this convention ensures compatibility.

### 9. Subsection labels must be sorted alphabetically
The subsection table entries in the rebuilt file must be ordered alphabetically by label name (FSHOP < ISHOP < SHOP_PERSON < WSHOP).

### 10. Backup files go in Backup/ folder
Keep original unmodified files in Backup/ folder, not as .bak alongside game files. This prevents them from being accidentally included when repacking the ISO.

### 11. Avoid special characters in project directory names
Colons in directory names (e.g., "Fire Emblem: Radiant Dawn") cause issues with many tools and Python file operations on Windows.

### 12. PRF bitmask data is multi-purpose
The 12-byte PRF appendix on item entries encodes different data depending on item type. For weapons it's character restriction bitmasks, for stat boosters it's the stat bonus values (HP/Str/Mag/Skl/Spd/Lck/Def/Res/Mov). Never blindly overwrite PRF data.

### 13. Use rank + eq* changes to unlock PRF weapons
Instead of modifying PRF bitmasks (which breaks stat items), change the weapon rank from "N" to "D" and remove the `eq*` attribute. This is the safe way to make personal weapons equippable by everyone.

### 14. Keep project directory names free of special characters
The original directory name "Fire Emblem: Radiant Dawn Claude Mod" (with colon) caused persistent issues with Python file I/O, Write tool creating parallel directories, and potential problems with game disc tools. Renamed to "Fire Emblem - Radiant Dawn Claude Mod".

## Tools & References
- Python 3.12+ for all scripts
- wit (Wiimms ISO Tools) for disc extraction/rebuilding: `wit COPY Game/ output.iso`
- fe10-randomizer (github.com/LordMewtwo73/fe10-randomizer) - reference implementation for CMS shop file format
- Dolphin Emulator for testing

## File Dependencies
- `rebuild_randomizer_style.py` reads from `Backup/*.bin` and `Game/DATA/files/FE10Data_decompressed.bin`
- `FE10Data_decompressed.bin` is generated by the price-zeroing step
- `item_database_output.txt` is documentation only, not a script dependency
