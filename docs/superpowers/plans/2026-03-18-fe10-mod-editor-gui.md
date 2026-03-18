# FE10 Mod Editor GUI — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a PySide6 desktop application that lets users edit FE10 item stats, customize per-chapter shop inventories, apply batch weapon modifications, and build mods to game files via a project-based workflow.

**Architecture:** The app follows a models/views/widgets/core layered architecture. `core/` contains pure-function binary format handlers extracted from the existing scripts (`mod_free_shop.py`, `rebuild_randomizer_style.py`). `models/` holds the data layer (item database, shop database, project state, build orchestration). `views/` and `widgets/` contain the PySide6 UI. The project file (`.fe10mod` JSON) stores only diffs from original game data.

**Tech Stack:** Python 3.12+, PySide6, pytest

**Spec:** `docs/superpowers/specs/2026-03-18-fe10-mod-editor-gui-design.md`

**Existing code reference:** `mod_free_shop.py` (LZ10, item parsing, FST), `rebuild_randomizer_style.py` (CMS shop builder)

---

## File Structure

```
fe10_mod_editor/
├── __init__.py
├── main.py                       # Entry point, QApplication setup, main window launch
├── core/
│   ├── __init__.py
│   ├── lz10.py                   # LZ10 compress/decompress (from mod_free_shop.py)
│   ├── cms_parser.py             # CMS format: string resolution, section parsing
│   ├── item_parser.py            # Parse ItemData section from decompressed FE10Data
│   ├── shop_parser.py            # Parse original shop files to extract per-chapter inventories
│   ├── shop_builder.py           # CompressShopfile algorithm (from rebuild_randomizer_style.py)
│   ├── fst_updater.py            # FST entry size patching
│   └── backup_manager.py         # MD5 hashing, verification, backup creation/restore
├── models/
│   ├── __init__.py
│   ├── item_data.py              # ItemEntry dataclass, ItemDatabase (in-memory collection)
│   ├── shop_data.py              # ShopInventory, ChapterShop, ShopDatabase
│   ├── project.py                # ProjectFile: load/save .fe10mod JSON, apply overlays
│   └── mod_builder.py            # Build pipeline orchestration, QThread worker
├── views/
│   ├── __init__.py
│   ├── main_window.py            # QMainWindow, tab bar, menu bar, status bar
│   ├── items_tab.py              # Items tab: table + side panel layout
│   ├── shops_tab.py              # Shops tab: chapter list + two-column inventory
│   ├── build_tab.py              # Build tab: paths, summary, build button, log
│   └── misc_tab.py               # Misc tab: toggle categories
├── widgets/
│   ├── __init__.py
│   ├── item_table.py             # QTableView + filter model for item list
│   ├── item_editor.py            # Side panel editor widget (combat stats, economy, etc.)
│   ├── shop_inventory.py         # Checkbox item list with Stock All / Clear buttons
│   └── toggle_card.py            # Toggle card widget for misc tab
└── tests/
    ├── __init__.py
    ├── test_lz10.py
    ├── test_cms_parser.py
    ├── test_item_parser.py
    ├── test_shop_parser.py
    ├── test_shop_builder.py
    ├── test_fst_updater.py
    ├── test_backup_manager.py
    ├── test_item_data.py
    ├── test_shop_data.py
    ├── test_project.py
    ├── test_mod_builder.py
    └── conftest.py                # Shared fixtures: sample binary data, paths
```

---

## Task 1: Project Scaffolding and Dependencies

**Files:**
- Create: `fe10_mod_editor/__init__.py`
- Create: `fe10_mod_editor/core/__init__.py`
- Create: `fe10_mod_editor/models/__init__.py`
- Create: `fe10_mod_editor/views/__init__.py`
- Create: `fe10_mod_editor/widgets/__init__.py`
- Create: `fe10_mod_editor/tests/__init__.py`
- Create: `requirements.txt`
- Create: `fe10_mod_editor/tests/conftest.py`

- [ ] **Step 1: Create requirements.txt**

```
PySide6>=6.6.0
pytest>=7.0.0
```

- [ ] **Step 2: Install dependencies**

Run: `pip install -r requirements.txt`
Expected: PySide6 and pytest install successfully

- [ ] **Step 3: Create all `__init__.py` files and conftest**

Create empty `__init__.py` in: `fe10_mod_editor/`, `fe10_mod_editor/core/`, `fe10_mod_editor/models/`, `fe10_mod_editor/views/`, `fe10_mod_editor/widgets/`, `fe10_mod_editor/tests/`.

Create `fe10_mod_editor/tests/conftest.py`:

```python
import os
import pytest

# Path to the project root (where Backup/, Game/ directories live)
PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR = os.path.join(PROJECT_ROOT, "Backup")
GAME_DATA_FILES = os.path.join(PROJECT_ROOT, "Game", "DATA", "files")
SHOP_DIR = os.path.join(GAME_DATA_FILES, "Shop")


@pytest.fixture
def backup_dir():
    """Path to the Backup directory containing original game files."""
    if not os.path.isdir(BACKUP_DIR):
        pytest.skip("Backup directory not found — need original game files for integration tests")
    return BACKUP_DIR


@pytest.fixture
def game_data_files():
    """Path to Game/DATA/files directory."""
    if not os.path.isdir(GAME_DATA_FILES):
        pytest.skip("Game data directory not found")
    return GAME_DATA_FILES


@pytest.fixture
def shop_dir():
    """Path to Game/DATA/files/Shop directory."""
    if not os.path.isdir(SHOP_DIR):
        pytest.skip("Shop directory not found")
    return SHOP_DIR
```

- [ ] **Step 4: Verify pytest discovers the test directory**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/ --collect-only`
Expected: "no tests ran" with no import errors

- [ ] **Step 5: Commit**

```bash
git add requirements.txt fe10_mod_editor/
git commit -m "feat: scaffold project structure with package layout and test fixtures"
```

---

## Task 2: LZ10 Compression/Decompression (`core/lz10.py`)

**Files:**
- Create: `fe10_mod_editor/core/lz10.py`
- Create: `fe10_mod_editor/tests/test_lz10.py`

Extract the `decompress_lz10` and `compress_lz10` functions from `mod_free_shop.py` (lines 102-193) into a standalone module. These are pure functions with no dependencies.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_lz10.py`:

```python
import os
import pytest
from fe10_mod_editor.core.lz10 import decompress_lz10, compress_lz10


def test_decompress_lz10_header_check():
    """LZ10 data must start with 0x10 signature byte."""
    with pytest.raises(ValueError, match="Not LZ10"):
        decompress_lz10(b"\x00\x00\x00\x00")


def test_decompress_lz10_literal_only():
    """Decompress a hand-crafted LZ10 payload with only literal bytes."""
    # Header: 0x10, size=3 (LE 24-bit: 03 00 00)
    # Flag byte: 0x00 (8 literal entries)
    # 3 literal bytes: 0x41 0x42 0x43 ("ABC")
    data = bytes([0x10, 0x03, 0x00, 0x00, 0x00, 0x41, 0x42, 0x43])
    result = decompress_lz10(data)
    assert result == b"ABC"


def test_roundtrip_small():
    """Compress then decompress should return original data."""
    original = b"AAAAAABBBBBBCCCCCC" * 10
    compressed = compress_lz10(original)
    decompressed = decompress_lz10(compressed)
    assert decompressed == original


def test_roundtrip_with_real_fe10data(backup_dir):
    """Roundtrip the actual FE10Data.cms backup file."""
    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()

    decompressed = decompress_lz10(compressed)
    # Verify decompressed data has the ItemData marker at 0xDF44
    assert len(decompressed) > 0xDF48

    recompressed = compress_lz10(decompressed)
    re_decompressed = decompress_lz10(recompressed)
    assert re_decompressed == decompressed
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_lz10.py -v`
Expected: FAIL — `ModuleNotFoundError: No module named 'fe10_mod_editor.core.lz10'`

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/lz10.py` — extract `decompress_lz10` and `compress_lz10` from `mod_free_shop.py` lines 102-193. Copy them verbatim (they are already self-contained pure functions with no external dependencies). Only change: add module docstring.

```python
"""LZ10 compression and decompression for Nintendo DS/Wii binary formats."""

import struct


def decompress_lz10(data: bytes) -> bytes:
    # ... exact copy from mod_free_shop.py lines 102-137 ...


def compress_lz10(data: bytes) -> bytes:
    # ... exact copy from mod_free_shop.py lines 143-193 ...
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_lz10.py -v`
Expected: All 4 tests PASS (the real-file test may skip if Backup/ is missing)

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/lz10.py fe10_mod_editor/tests/test_lz10.py
git commit -m "feat: extract LZ10 compress/decompress into core/lz10.py"
```

---

## Task 3: CMS String Resolution (`core/cms_parser.py`)

**Files:**
- Create: `fe10_mod_editor/core/cms_parser.py`
- Create: `fe10_mod_editor/tests/test_cms_parser.py`

Extract the `resolve_string` function and add a CMS header parser. The `resolve_string` function appears in both existing scripts (both identical). The CMS header parser reads the 4-field header used by shop files.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_cms_parser.py`:

```python
import struct
import pytest
from fe10_mod_editor.core.cms_parser import resolve_string, parse_cms_header


def test_resolve_string_null_pointer():
    """Pointer value 0 returns None."""
    data = b"\x00" * 100
    assert resolve_string(data, 0) is None


def test_resolve_string_valid():
    """Resolve a pointer to an ASCII string in the data region."""
    # Place "HELLO\0" at file offset 0x30
    # Stored pointer = 0x30 - 0x20 = 0x10
    data = bytearray(0x40)
    data[0x30:0x36] = b"HELLO\x00"
    assert resolve_string(bytes(data), 0x10) == "HELLO"


def test_resolve_string_out_of_bounds():
    """Pointer beyond data length returns None."""
    data = b"\x00" * 10
    assert resolve_string(data, 0xFFFF) is None


def test_parse_cms_header():
    """Parse the 4-field CMS header."""
    header = struct.pack(">IIII", 1000, 500, 42, 10)
    header += b"\x00" * 24  # padding to 40 bytes
    result = parse_cms_header(header)
    assert result["file_size"] == 1000
    assert result["data_region_size"] == 500
    assert result["ptr1_count"] == 42
    assert result["ptr2_count"] == 10
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_cms_parser.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/cms_parser.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_cms_parser.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/cms_parser.py fe10_mod_editor/tests/test_cms_parser.py
git commit -m "feat: add CMS string resolution and header parsing to core/cms_parser.py"
```

---

## Task 4: Item Parser (`core/item_parser.py`)

**Files:**
- Create: `fe10_mod_editor/core/item_parser.py`
- Create: `fe10_mod_editor/tests/test_item_parser.py`

Parse the ItemData section from decompressed FE10Data. This extracts from `mod_free_shop.py`'s modify_fe10data (the parsing loop) and `rebuild_randomizer_style.py`'s parse_items. Returns structured data — does NOT modify anything.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_item_parser.py`:

```python
import os
import pytest
from fe10_mod_editor.core.item_parser import parse_all_items, ITEM_DATA_OFFSET


def test_parse_all_items_returns_296(backup_dir):
    """Parse the real FE10Data and expect 296 items."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)

    items = parse_all_items(data)
    assert len(items) == 296


def test_parse_item_has_expected_fields(backup_dir):
    """Each parsed item has all required fields."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)

    items = parse_all_items(data)
    first = items[0]

    required_fields = [
        "iid", "weapon_type", "weapon_rank", "price", "might", "accuracy",
        "critical", "weight", "uses", "wexp_gain", "min_range", "max_range",
        "attributes", "effectiveness_count", "prf_flag", "icon_id",
        "byte_offset",
    ]
    for field in required_fields:
        assert field in first, f"Missing field: {field}"


def test_parse_items_finds_iron_sword(backup_dir):
    """Verify IID_IRON_SWORD is parsed with expected stats."""
    from fe10_mod_editor.core.lz10 import decompress_lz10

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)

    items = parse_all_items(data)
    iron_sword = next((i for i in items if i["iid"] == "IID_IRON_SWORD"), None)
    assert iron_sword is not None
    assert iron_sword["weapon_type"] == "sword"
    assert iron_sword["weapon_rank"] in ("E", "D", "C", "B", "A", "S", "N")
    assert iron_sword["might"] > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_item_parser.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/item_parser.py`:

```python
"""Parse the ItemData section from decompressed FE10Data binary.

Item entries start at offset 0xDF44. The first 4 bytes are the item count (u32 BE).
Each item has a 56-byte fixed header followed by variable-length trailing data
(attribute pointers, effectiveness pointers, PRF data).

See the design spec's Binary Format Reference for the full field layout.
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_item_parser.py -v`
Expected: All 3 tests PASS (or skip if Backup/ missing)

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/item_parser.py fe10_mod_editor/tests/test_item_parser.py
git commit -m "feat: add item parser to extract all 296 items from FE10Data binary"
```

---

## Task 5: Shop Parser (`core/shop_parser.py`)

**Files:**
- Create: `fe10_mod_editor/core/shop_parser.py`
- Create: `fe10_mod_editor/tests/test_shop_parser.py`

Extract the shop file parsing logic from `rebuild_randomizer_style.py`'s `parse_original` function. This reads a shop binary and returns the per-chapter inventories, SHOP_PERSON data, FSHOP data, and FSHOP_CARD data.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_shop_parser.py`:

```python
import os
import pytest
from fe10_mod_editor.core.shop_parser import parse_shop_file, CHAPTERS, TUTORIALS


def test_parse_shop_file_returns_all_sections(backup_dir):
    """Parsing a real shop file returns all expected sections."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    result = parse_shop_file(shop_path)

    assert "shop_person_data" in result
    assert "wshop_items" in result
    assert "ishop_items" in result
    assert "fshop_data" in result
    assert "fshop_card_entries" in result


def test_parse_shop_file_has_all_chapters(backup_dir):
    """SHOP_PERSON data has entries for all 43 chapters + 4 tutorials."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    result = parse_shop_file(shop_path)

    assert len(result["shop_person_data"]) == 47
    for ch in CHAPTERS + TUTORIALS:
        assert ch in result["shop_person_data"]


def test_parse_shop_file_wshop_keys_are_chapters(backup_dir):
    """WSHOP items are keyed by chapter ID."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    result = parse_shop_file(shop_path)

    for ch in CHAPTERS:
        assert ch in result["wshop_items"]
        # Each value is a list of IID strings
        assert isinstance(result["wshop_items"][ch], list)


def test_parse_shop_file_fshop_has_43_chapters(backup_dir):
    """FSHOP data has exactly 43 chapter entries."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    result = parse_shop_file(shop_path)

    assert len(result["fshop_data"]) == 43
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_shop_parser.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/shop_parser.py`. This is extracted from `rebuild_randomizer_style.py`'s `parse_original` function (lines 107-251), restructured to return per-chapter item IID lists instead of just counts.

```python
"""Parse CMS shop files to extract per-chapter inventories and forge data.

Shop files (shopitem_n/m/h.bin) use a CMS container format. This module
reads the original shop files and extracts:
- SHOP_PERSON raw flag data (47 entries)
- WSHOP per-chapter weapon IID lists (43 chapters)
- ISHOP per-chapter consumable IID lists (43 chapters)
- FSHOP forge data (43 chapters, passed through unchanged)
- FSHOP_CARD forge card metadata (passed through unchanged)
"""

import struct
from fe10_mod_editor.core.cms_parser import resolve_string, parse_cms_header

CHAPTERS = [
    "C0000", "C0101", "C0102", "C0103", "C0104", "C0105", "C0106",
    "C0107", "C0108", "C0109", "C0110", "C0111",
    "C0201", "C0202", "C0203", "C0204", "C0205",
    "C0301", "C0302", "C0303", "C0304", "C0305", "C0306", "C0307",
    "C0308", "C0309", "C0310", "C0311", "C0312", "C0313", "C0314", "C0315",
    "C0401", "C0402", "C0403", "C0404", "C0405", "C0406",
    "C0407a", "C0407b", "C0407c", "C0407d", "C0407e",
]
TUTORIALS = ["T01", "T02", "T03", "T04"]


def parse_shop_file(filepath: str) -> dict:
    """Parse a shop file and return all sections.

    Args:
        filepath: Path to a shopitem_*.bin file.

    Returns:
        Dict with keys:
        - shop_person_data: dict[str, bytes] — chapter_id -> 4 raw bytes
        - wshop_items: dict[str, list[str]] — chapter_id -> list of weapon IIDs
        - ishop_items: dict[str, list[str]] — chapter_id -> list of item IIDs
        - fshop_data: dict[str, list[tuple]] — chapter_id -> list of (value, string|None)
        - fshop_card_entries: list[tuple] — (mess_string, raw_bytes)
    """
    with open(filepath, "rb") as f:
        orig = f.read()

    header = parse_cms_header(orig)
    data_start = 0x20
    ptr1_start = data_start + header["data_region_size"]
    ptr2_start = ptr1_start + header["ptr1_count"] * 4
    label_start = ptr2_start + header["ptr2_count"] * 8

    # Build pointer table 1 set (identifies which data offsets contain string pointers)
    pt1_set = set()
    for i in range(header["ptr1_count"]):
        off = ptr1_start + i * 4
        val = struct.unpack(">I", orig[off:off + 4])[0]
        pt1_set.add(val)

    # Parse subsection table (Pointer Table 2)
    sub_entries = []
    for i in range(header["ptr2_count"]):
        off = ptr2_start + i * 8
        data_off, label_off = struct.unpack(">II", orig[off:off + 8])
        lbl_abs = label_start + label_off
        lbl_end = orig.index(b"\x00", lbl_abs)
        label = orig[lbl_abs:lbl_end].decode("ascii")
        sub_entries.append((label, data_off))

    sub_dict = {label: data_off for label, data_off in sub_entries}

    # SHOP_PERSON: 47 entries of 4 raw bytes each
    shop_person_data = {}
    for ch in CHAPTERS + TUTORIALS:
        label = "SHOP_PERSON_" + ch
        doff = sub_dict[label]
        abs_off = data_start + doff
        shop_person_data[ch] = orig[abs_off:abs_off + 4]

    # Sort shop subsections by data offset for boundary calculation
    wshop_sorted = sorted(
        [(l, o) for l, o in sub_entries if l.startswith("WSHOP_ITEMS_")],
        key=lambda x: x[1],
    )
    ishop_sorted = sorted(
        [(l, o) for l, o in sub_entries if l.startswith("ISHOP_ITEMS_")],
        key=lambda x: x[1],
    )
    fshop_sorted = sorted(
        [(l, o) for l, o in sub_entries if l.startswith("FSHOP_ITEMS_")],
        key=lambda x: x[1],
    )

    # Parse WSHOP: extract IID strings per chapter
    wshop_items = {}
    for i, (label, off) in enumerate(wshop_sorted):
        ch = label.replace("WSHOP_ITEMS_", "")
        if i + 1 < len(wshop_sorted):
            next_off = wshop_sorted[i + 1][1]
        else:
            next_off = ishop_sorted[0][1]

        items = []
        j = 0
        total_bytes = next_off - off
        while j < total_bytes - 4:
            val = struct.unpack(">I", orig[data_start + off + j:data_start + off + j + 4])[0]
            if val != 0:
                iid = resolve_string(orig, val)
                if iid:
                    items.append(iid)
            j += 8  # Each entry is 8 bytes (IID ptr + 4 zero bytes)
        wshop_items[ch] = items

    # Parse ISHOP: extract IID strings per chapter
    ishop_items = {}
    for i, (label, off) in enumerate(ishop_sorted):
        ch = label.replace("ISHOP_ITEMS_", "")
        if i + 1 < len(ishop_sorted):
            next_off = ishop_sorted[i + 1][1]
        else:
            next_off = fshop_sorted[0][1]

        items = []
        total_bytes = next_off - off
        if total_bytes > 4:
            j = 0
            while j < total_bytes - 4:
                val = struct.unpack(">I", orig[data_start + off + j:data_start + off + j + 4])[0]
                if val != 0:
                    iid = resolve_string(orig, val)
                    if iid:
                        items.append(iid)
                j += 8
        ishop_items[ch] = items

    # Parse FSHOP: 43 chapters, each 180 dwords (720 bytes)
    fshop_data = {}
    for label, off in fshop_sorted:
        ch = label.replace("FSHOP_ITEMS_", "")
        abs_off = data_start + off
        dwords = []
        for d in range(180):
            val = struct.unpack(">I", orig[abs_off + d * 4:abs_off + d * 4 + 4])[0]
            doff = off + d * 4
            if val == 0:
                dwords.append((0, None))
            elif doff in pt1_set:
                s = resolve_string(orig, val)
                dwords.append((val, s))
            else:
                dwords.append((val, None))
        fshop_data[ch] = dwords

    # Parse FSHOP_CARD
    fshop_card_off = sub_dict["FSHOP_CARD_DATA"]
    fshop_card_abs = data_start + fshop_card_off
    card_count = orig[fshop_card_abs + 3]

    fshop_card_entries = []
    for i in range(card_count):
        entry_start = fshop_card_abs + 4 + i * 12
        mess_ptr = struct.unpack(">I", orig[entry_start:entry_start + 4])[0]
        mess_str = resolve_string(orig, mess_ptr)
        raw_bytes = orig[entry_start + 4:entry_start + 12]
        fshop_card_entries.append((mess_str, raw_bytes))

    return {
        "chapters": CHAPTERS,
        "tutorials": TUTORIALS,
        "shop_person_data": shop_person_data,
        "wshop_items": wshop_items,
        "ishop_items": ishop_items,
        "fshop_data": fshop_data,
        "fshop_card_entries": fshop_card_entries,
    }
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_shop_parser.py -v`
Expected: All 4 tests PASS (or skip if Backup/ missing)

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/shop_parser.py fe10_mod_editor/tests/test_shop_parser.py
git commit -m "feat: add shop file parser to extract per-chapter inventories"
```

---

## Task 6: Shop Builder (`core/shop_builder.py`)

**Files:**
- Create: `fe10_mod_editor/core/shop_builder.py`
- Create: `fe10_mod_editor/tests/test_shop_builder.py`

Extract the `build_shop_file` function from `rebuild_randomizer_style.py` (lines 257-421). This is the CompressShopfile algorithm that constructs a complete CMS shop file from scratch. Keep it as a pure function that takes structured data and returns bytes.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_shop_builder.py`:

```python
import os
import struct
import pytest
from fe10_mod_editor.core.shop_builder import build_shop_file
from fe10_mod_editor.core.shop_parser import parse_shop_file
from fe10_mod_editor.core.cms_parser import parse_cms_header


def test_build_shop_file_produces_valid_cms(backup_dir):
    """Build a shop file and verify the CMS header is consistent."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    orig_info = parse_shop_file(shop_path)

    # Use a small subset of items for speed
    wshop = ["IID_IRON_SWORD", "IID_STEEL_SWORD"]
    ishop = ["IID_VULNERARY"]

    result = build_shop_file(orig_info, wshop, ishop)
    header = parse_cms_header(result)

    assert header["file_size"] == len(result)
    assert header["ptr1_count"] > 0
    assert header["ptr2_count"] > 0


def test_build_shop_file_roundtrip(backup_dir):
    """Build a shop file, then parse it back — subsection labels should match."""
    shop_path = os.path.join(backup_dir, "shopitem_n.bin")
    orig_info = parse_shop_file(shop_path)

    wshop = ["IID_IRON_SWORD"]
    ishop = ["IID_VULNERARY"]

    result = build_shop_file(orig_info, wshop, ishop)

    # Write to temp file and parse back
    import tempfile
    with tempfile.NamedTemporaryFile(suffix=".bin", delete=False) as f:
        f.write(result)
        tmp_path = f.name

    try:
        parsed_back = parse_shop_file(tmp_path)
        # Should have same chapters in WSHOP
        assert set(parsed_back["wshop_items"].keys()) == set(orig_info["wshop_items"].keys())
        # Each chapter should have our 1 weapon
        for ch_items in parsed_back["wshop_items"].values():
            assert ch_items == ["IID_IRON_SWORD"]
    finally:
        os.unlink(tmp_path)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_shop_builder.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/shop_builder.py` — extract `build_shop_file` from `rebuild_randomizer_style.py` lines 257-421. Adapt the function signature to accept the structured dict from `parse_shop_file` plus the weapon/item IID lists.

Adapt the existing `build_shop_file` from `rebuild_randomizer_style.py`. Key changes from the original:
- Import `CHAPTERS` and `TUTORIALS` from `shop_parser` instead of reading them from `orig_info`
- Read `chapters` and `tutorials` from `orig_info` (which now includes them from `parse_shop_file`)
- The function no longer needs `wshop_counts`/`ishop_counts` — it receives explicit item lists to stock
- The original's `orig_info["wshop_counts"]` and `orig_info["ishop_counts"]` fields are replaced by `wshop_items` and `ishop_items` parameters (lists of IID strings)

```python
"""Build CMS shop files using the CompressShopfile algorithm.

This is a direct extraction of the algorithm from rebuild_randomizer_style.py.
It constructs a complete CMS shop binary from structured data.
"""

import struct
from fe10_mod_editor.core.shop_parser import CHAPTERS, TUTORIALS


def build_shop_file(
    orig_info: dict,
    wshop_items: list[str] | dict[str, list[str]],
    ishop_items: list[str] | dict[str, list[str]],
) -> bytes:
    """Build a complete CMS shop file.

    Args:
        orig_info: Dict from parse_shop_file() containing chapters, tutorials,
                   shop_person_data, fshop_data, fshop_card_entries.
        wshop_items: Either a flat list of weapon IIDs (applied to all chapters)
                     or a dict of chapter_id -> list of weapon IIDs (per-chapter).
        ishop_items: Either a flat list of item IIDs (applied to all chapters)
                     or a dict of chapter_id -> list of item IIDs (per-chapter).

    Returns:
        Complete CMS shop file as bytes.
    """
    chapters = orig_info["chapters"]
    tutorials = orig_info["tutorials"]

    # Normalize to per-chapter dicts
    if isinstance(wshop_items, list):
        _wshop = {ch: wshop_items for ch in chapters}
    else:
        _wshop = wshop_items

    if isinstance(ishop_items, list):
        _ishop = {ch: ishop_items for ch in chapters}
    else:
        _ishop = ishop_items

    # ... rest of build_shop_file from rebuild_randomizer_style.py lines 266-421 ...
    # Replace the WSHOP loop to use _wshop[ch] instead of flat wshop_items:
    #   for ch in chapters:
    #       labels.append("WSHOP_ITEMS_" + ch)
    #       dataoffsets.append(len(out))
    #       for iid in _wshop.get(ch, []):
    #           ...
    # Same pattern for ISHOP loop using _ishop[ch]
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_shop_builder.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/shop_builder.py fe10_mod_editor/tests/test_shop_builder.py
git commit -m "feat: extract CompressShopfile algorithm into core/shop_builder.py"
```

---

## Task 7: FST Updater (`core/fst_updater.py`)

**Files:**
- Create: `fe10_mod_editor/core/fst_updater.py`
- Create: `fe10_mod_editor/tests/test_fst_updater.py`

Extract the FST patching logic from `mod_free_shop.py`'s `update_fst` function (lines 422-472). Pure function that takes FST data + size map, returns patched FST data.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_fst_updater.py`:

```python
import struct
import pytest
from fe10_mod_editor.core.fst_updater import patch_fst_sizes, FST_SHOP_INDICES


def test_patch_fst_sizes_updates_entries():
    """Patching FST data updates the size fields at correct offsets."""
    # Create fake FST data large enough for the highest index
    max_index = max(FST_SHOP_INDICES.values())
    fst_size = (max_index + 1) * 12
    fst_data = bytearray(fst_size)

    # Set original sizes to 1000 for each shop entry
    for fname, idx in FST_SHOP_INDICES.items():
        struct.pack_into(">I", fst_data, idx * 12 + 8, 1000)

    new_sizes = {
        "shopitem_h.bin": 183068,
        "shopitem_m.bin": 183068,
        "shopitem_n.bin": 183068,
    }

    patched = patch_fst_sizes(bytes(fst_data), new_sizes)

    for fname, idx in FST_SHOP_INDICES.items():
        size_off = idx * 12 + 8
        actual = struct.unpack(">I", patched[size_off:size_off + 4])[0]
        assert actual == 183068


def test_patch_fst_sizes_preserves_other_data():
    """Patching only modifies the target entries, not other data."""
    max_index = max(FST_SHOP_INDICES.values())
    fst_size = (max_index + 1) * 12
    fst_data = bytearray(fst_size)

    # Write a sentinel value at index 0
    struct.pack_into(">I", fst_data, 8, 0xDEADBEEF)

    new_sizes = {
        "shopitem_h.bin": 100,
        "shopitem_m.bin": 200,
        "shopitem_n.bin": 300,
    }

    patched = patch_fst_sizes(bytes(fst_data), new_sizes)
    sentinel = struct.unpack(">I", patched[8:12])[0]
    assert sentinel == 0xDEADBEEF
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_fst_updater.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/fst_updater.py`:

```python
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
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_fst_updater.py -v`
Expected: All 2 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/fst_updater.py fe10_mod_editor/tests/test_fst_updater.py
git commit -m "feat: add FST size patching utility"
```

---

## Task 8: Backup Manager (`core/backup_manager.py`)

**Files:**
- Create: `fe10_mod_editor/core/backup_manager.py`
- Create: `fe10_mod_editor/tests/test_backup_manager.py`

MD5 hash computation, verification against stored hashes, backup creation with write-once policy, and restore functionality.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_backup_manager.py`:

```python
import os
import tempfile
import pytest
from fe10_mod_editor.core.backup_manager import (
    compute_file_hash,
    verify_backup_hashes,
    compute_backup_hashes,
    BACKUP_FILES,
)


def test_compute_file_hash_deterministic(tmp_path):
    """Same content always produces same hash."""
    path = tmp_path / "test.bin"
    path.write_bytes(b"hello world")
    h1 = compute_file_hash(str(path))
    h2 = compute_file_hash(str(path))
    assert h1 == h2
    assert len(h1) == 32  # MD5 hex digest length


def test_compute_file_hash_different_content(tmp_path):
    """Different content produces different hash."""
    p1 = tmp_path / "a.bin"
    p2 = tmp_path / "b.bin"
    p1.write_bytes(b"hello")
    p2.write_bytes(b"world")
    assert compute_file_hash(str(p1)) != compute_file_hash(str(p2))


def test_verify_backup_hashes_pass(tmp_path):
    """Verification passes when files match stored hashes."""
    p = tmp_path / "test.bin"
    p.write_bytes(b"data")
    h = compute_file_hash(str(p))
    result = verify_backup_hashes(str(tmp_path), {"test.bin": h})
    assert result.ok is True


def test_verify_backup_hashes_fail_mismatch(tmp_path):
    """Verification fails when file content doesn't match hash."""
    p = tmp_path / "test.bin"
    p.write_bytes(b"data")
    result = verify_backup_hashes(str(tmp_path), {"test.bin": "0000000000000000"})
    assert result.ok is False
    assert "mismatch" in result.error.lower()


def test_verify_backup_hashes_fail_missing(tmp_path):
    """Verification fails when expected file is missing."""
    result = verify_backup_hashes(str(tmp_path), {"missing.bin": "abc123"})
    assert result.ok is False


def test_compute_backup_hashes_real_files(backup_dir):
    """Compute hashes for real backup files."""
    hashes = compute_backup_hashes(backup_dir)
    for fname in BACKUP_FILES:
        assert fname in hashes
        assert len(hashes[fname]) == 32
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_backup_manager.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/core/backup_manager.py`:

```python
"""Backup file management with MD5 hash verification.

Backup safety rules:
1. Backups contain only original unmodified files
2. MD5 hashes are computed once on first backup, stored in project file
3. Write-once: never overwrite a verified backup
4. Verify before every build: abort on hash mismatch
"""

import hashlib
import os
import shutil
from dataclasses import dataclass

BACKUP_FILES = [
    "FE10Data.cms",
    "shopitem_n.bin",
    "shopitem_m.bin",
    "shopitem_h.bin",
    "fst.bin",
]


@dataclass
class VerifyResult:
    ok: bool
    error: str = ""


def compute_file_hash(filepath: str) -> str:
    """Compute MD5 hash of a file. Returns hex digest string."""
    md5 = hashlib.md5()
    with open(filepath, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            md5.update(chunk)
    return md5.hexdigest()


def compute_backup_hashes(backup_dir: str) -> dict[str, str]:
    """Compute MD5 hashes for all expected backup files.

    Args:
        backup_dir: Path to directory containing original game files.

    Returns:
        Dict of filename -> MD5 hex digest.

    Raises:
        FileNotFoundError: If any expected file is missing.
    """
    hashes = {}
    for fname in BACKUP_FILES:
        path = os.path.join(backup_dir, fname)
        if not os.path.exists(path):
            raise FileNotFoundError(f"Missing backup file: {fname}")
        hashes[fname] = compute_file_hash(path)
    return hashes


def verify_backup_hashes(backup_dir: str, stored_hashes: dict[str, str]) -> VerifyResult:
    """Verify backup files against stored MD5 hashes.

    Args:
        backup_dir: Path to backup directory.
        stored_hashes: Dict of filename -> expected MD5 hex digest.

    Returns:
        VerifyResult with ok=True if all match, or ok=False with error message.
    """
    for fname, expected_hash in stored_hashes.items():
        path = os.path.join(backup_dir, fname)
        if not os.path.exists(path):
            return VerifyResult(ok=False, error=f"Missing file: {fname}")
        actual_hash = compute_file_hash(path)
        if actual_hash != expected_hash:
            return VerifyResult(
                ok=False,
                error=f"Hash mismatch for {fname}: expected {expected_hash}, got {actual_hash}",
            )
    return VerifyResult(ok=True)


def restore_backup(backup_dir: str, game_dir: str, shop_dir: str, fst_path: str) -> list[str]:
    """Copy all backup files back to their game directory locations.

    Args:
        backup_dir: Source directory with original files.
        game_dir: Target for FE10Data.cms (Game/DATA/files/).
        shop_dir: Target for shop files (Game/DATA/files/Shop/).
        fst_path: Full target path for fst.bin (Game/DATA/sys/fst.bin).

    Returns:
        List of restored file paths.
    """
    restored = []

    targets = {
        "FE10Data.cms": os.path.join(game_dir, "FE10Data.cms"),
        "shopitem_n.bin": os.path.join(shop_dir, "shopitem_n.bin"),
        "shopitem_m.bin": os.path.join(shop_dir, "shopitem_m.bin"),
        "shopitem_h.bin": os.path.join(shop_dir, "shopitem_h.bin"),
        "fst.bin": fst_path,
    }

    for fname, target_path in targets.items():
        src = os.path.join(backup_dir, fname)
        if os.path.exists(src):
            shutil.copy2(src, target_path)
            restored.append(target_path)

    return restored
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_backup_manager.py -v`
Expected: All 6 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/core/backup_manager.py fe10_mod_editor/tests/test_backup_manager.py
git commit -m "feat: add backup manager with MD5 verification and write-once policy"
```

---

## Task 9: Item Data Model (`models/item_data.py`)

**Files:**
- Create: `fe10_mod_editor/models/item_data.py`
- Create: `fe10_mod_editor/tests/test_item_data.py`

The `ItemEntry` dataclass wraps parsed item data. `ItemDatabase` holds the full collection and provides filtering/lookup. It also handles the display name transformation and shop-eligibility classification from the spec.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_item_data.py`:

```python
import pytest
from fe10_mod_editor.models.item_data import ItemEntry, ItemDatabase, display_name_from_iid


def test_display_name_from_iid():
    assert display_name_from_iid("IID_IRON_SWORD") == "Iron Sword"
    assert display_name_from_iid("IID_VULNERARY") == "Vulnerary"
    assert display_name_from_iid("IID_STEEL_BOW") == "Steel Bow"


def test_item_entry_creation():
    item = ItemEntry(
        iid="IID_IRON_SWORD", display_type="sword", weapon_type="sword", weapon_rank="E",
        price=560, might=5, accuracy=100, critical=0, weight=5,
        uses=45, wexp_gain=2, min_range=1, max_range=1,
        attributes=[], effectiveness_count=0, prf_flag=0,
        icon_id=0, byte_offset=0,
    )
    assert item.display_name == "Iron Sword"
    assert item.is_weapon is True
    assert item.is_shop_eligible is True


def test_item_database_from_parsed(backup_dir):
    """Build ItemDatabase from real parsed data."""
    import os
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.item_parser import parse_all_items

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    data = decompress_lz10(compressed)
    parsed = parse_all_items(data)

    db = ItemDatabase.from_parsed_items(parsed)
    assert db.count == 296
    assert len(db.weapon_shop_items) == 126
    assert len(db.item_shop_items) == 109
    assert db.get("IID_IRON_SWORD") is not None


def test_item_database_filter_by_type(backup_dir):
    """Filter items by weapon type."""
    import os
    from fe10_mod_editor.core.lz10 import decompress_lz10
    from fe10_mod_editor.core.item_parser import parse_all_items

    cms_path = os.path.join(backup_dir, "FE10Data.cms")
    with open(cms_path, "rb") as f:
        compressed = f.read()
    parsed = parse_all_items(decompress_lz10(compressed))

    db = ItemDatabase.from_parsed_items(parsed)
    swords = db.filter_by_type("sword")
    assert len(swords) > 0
    assert all(i.weapon_type == "sword" for i in swords)
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_item_data.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/models/item_data.py`:

```python
"""Item data model — wraps parsed item data with display logic and filtering.

ItemEntry is the per-item data structure. ItemDatabase is the in-memory
collection that provides lookup, filtering, and shop-eligibility classification.
"""

from dataclasses import dataclass, field

WEAPON_TYPES = {
    "sword", "lance", "axe", "bow", "knife",
    "flame", "thunder", "wind", "light", "dark",
    "card", "ballista",
}

EXCLUDE_PREFIXES = [
    "IID_JOG_", "IID_JUDGE", "IID_SPRT_HEAL",
    "IID_DHEGINHANSEA", "IID_LEKAIN", "IID_CEPHERAN",
]


def display_name_from_iid(iid: str) -> str:
    """Convert IID to display name: strip 'IID_', replace '_' with ' ', title case."""
    name = iid
    if name.startswith("IID_"):
        name = name[4:]
    return name.replace("_", " ").title()


@dataclass
class ItemEntry:
    iid: str
    display_type: str  # offset +12, used for shop classification (matches existing code)
    weapon_type: str   # offset +16, actual weapon type
    weapon_rank: str
    price: int
    might: int
    accuracy: int
    critical: int
    weight: int
    uses: int
    wexp_gain: int
    min_range: int
    max_range: int
    attributes: list[str] = field(default_factory=list)
    effectiveness_count: int = 0
    prf_flag: int = 0
    icon_id: int = 0
    byte_offset: int = 0

    @property
    def display_name(self) -> str:
        return display_name_from_iid(self.iid)

    @property
    def is_weapon(self) -> bool:
        # Use display_type (offset +12) for classification, matching the
        # proven logic in rebuild_randomizer_style.py which uses disp_ptr (+12)
        return self.display_type in WEAPON_TYPES

    @property
    def is_shop_eligible(self) -> bool:
        if "blow" in self.attributes:
            return False
        if any(self.iid.startswith(p) for p in EXCLUDE_PREFIXES):
            return False
        if "longfar" in self.attributes and "sh" in self.attributes:
            return False
        if "stone" in self.attributes:
            return False
        return True

    @property
    def has_prf(self) -> bool:
        return self.weapon_rank == "N" or self.prf_flag == 1


class ItemDatabase:
    def __init__(self, items: list[ItemEntry]):
        self._items = items
        self._by_iid = {item.iid: item for item in items}

    @classmethod
    def from_parsed_items(cls, parsed: list[dict]) -> "ItemDatabase":
        entries = [
            ItemEntry(
                iid=p["iid"], display_type=p["display_type"],
                weapon_type=p["weapon_type"], weapon_rank=p["weapon_rank"],
                price=p["price"], might=p["might"], accuracy=p["accuracy"],
                critical=p["critical"], weight=p["weight"], uses=p["uses"],
                wexp_gain=p["wexp_gain"], min_range=p["min_range"], max_range=p["max_range"],
                attributes=p["attributes"], effectiveness_count=p["effectiveness_count"],
                prf_flag=p["prf_flag"], icon_id=p["icon_id"], byte_offset=p["byte_offset"],
            )
            for p in parsed
        ]
        return cls(entries)

    @property
    def count(self) -> int:
        return len(self._items)

    @property
    def all_items(self) -> list[ItemEntry]:
        return list(self._items)

    @property
    def weapon_shop_items(self) -> list[ItemEntry]:
        return [i for i in self._items if i.is_shop_eligible and i.is_weapon]

    @property
    def item_shop_items(self) -> list[ItemEntry]:
        return [i for i in self._items if i.is_shop_eligible and not i.is_weapon]

    def get(self, iid: str) -> ItemEntry | None:
        return self._by_iid.get(iid)

    def filter_by_type(self, weapon_type: str) -> list[ItemEntry]:
        return [i for i in self._items if i.weapon_type == weapon_type]

    @property
    def weapon_types(self) -> list[str]:
        return sorted(set(i.weapon_type for i in self._items if i.weapon_type))
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_item_data.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/models/item_data.py fe10_mod_editor/tests/test_item_data.py
git commit -m "feat: add ItemEntry dataclass and ItemDatabase with filtering and shop eligibility"
```

---

## Task 10: Shop Data Model (`models/shop_data.py`)

**Files:**
- Create: `fe10_mod_editor/models/shop_data.py`
- Create: `fe10_mod_editor/tests/test_shop_data.py`

Wraps parsed shop data into a model that supports the unified-with-overrides editing pattern and the difficulty override resolution algorithm from the spec.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_shop_data.py`:

```python
import pytest
from fe10_mod_editor.models.shop_data import ShopDatabase


def test_shop_database_resolve_unified():
    """Unified edit completely replaces vanilla inventory."""
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A", "IID_B"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    db.set_unified("C0101", weapons=["IID_X", "IID_Y", "IID_Z"])

    resolved = db.resolve("C0101", "normal")
    assert resolved["weapons"] == ["IID_X", "IID_Y", "IID_Z"]
    assert resolved["items"] == ["IID_V"]  # unchanged, no unified item edit


def test_shop_database_resolve_override_replaces_per_type():
    """Difficulty override replaces unified per shop type independently."""
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    db.set_unified("C0101", weapons=["IID_X", "IID_Y"], items=["IID_W"])
    db.set_override("C0101", "hard", weapons=["IID_Z"])

    # Hard: weapons overridden, items inherited from unified
    resolved_hard = db.resolve("C0101", "hard")
    assert resolved_hard["weapons"] == ["IID_Z"]
    assert resolved_hard["items"] == ["IID_W"]

    # Normal: uses unified (no override)
    resolved_normal = db.resolve("C0101", "normal")
    assert resolved_normal["weapons"] == ["IID_X", "IID_Y"]
    assert resolved_normal["items"] == ["IID_W"]


def test_shop_database_resolve_vanilla_fallback():
    """No edits returns vanilla inventory."""
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A", "IID_B"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    resolved = db.resolve("C0101", "normal")
    assert resolved["weapons"] == ["IID_A", "IID_B"]
    assert resolved["items"] == ["IID_V"]


def test_shop_database_to_dict_and_from_dict():
    """Round-trip through dict serialization."""
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    db.set_unified("C0101", weapons=["IID_X"])
    db.set_override("C0101", "hard", weapons=["IID_Z"])

    d = db.to_dict()
    db2 = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    db2.load_from_dict(d)

    assert db2.resolve("C0101", "hard") == db.resolve("C0101", "hard")
    assert db2.resolve("C0101", "normal") == db.resolve("C0101", "normal")
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_shop_data.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/models/shop_data.py`:

```python
"""Shop data model with unified-with-overrides editing pattern.

Difficulty override resolution (from spec):
1. Start with vanilla inventory
2. Unified edit completely replaces vanilla for that chapter
3. Difficulty override replaces unified per shop type (weapons/items independently)
"""


class ShopDatabase:
    def __init__(self, vanilla_weapons: dict[str, list[str]], vanilla_items: dict[str, list[str]]):
        self._vanilla_weapons = vanilla_weapons
        self._vanilla_items = vanilla_items
        self._unified: dict[str, dict] = {}  # chapter -> {"weapons": [...], "items": [...]}
        self._overrides: dict[str, dict[str, dict]] = {}  # difficulty -> chapter -> {"weapons": [...], ...}

    def set_unified(self, chapter: str, weapons: list[str] | None = None, items: list[str] | None = None):
        if chapter not in self._unified:
            self._unified[chapter] = {}
        if weapons is not None:
            self._unified[chapter]["weapons"] = weapons
        if items is not None:
            self._unified[chapter]["items"] = items

    def set_override(self, chapter: str, difficulty: str, weapons: list[str] | None = None, items: list[str] | None = None):
        if difficulty not in self._overrides:
            self._overrides[difficulty] = {}
        if chapter not in self._overrides[difficulty]:
            self._overrides[difficulty][chapter] = {}
        if weapons is not None:
            self._overrides[difficulty][chapter]["weapons"] = weapons
        if items is not None:
            self._overrides[difficulty][chapter]["items"] = items

    def resolve(self, chapter: str, difficulty: str) -> dict[str, list[str]]:
        """Resolve the final inventory for a chapter + difficulty.

        Returns dict with "weapons" and "items" lists.
        """
        # Step 1: Start with vanilla
        weapons = list(self._vanilla_weapons.get(chapter, []))
        items = list(self._vanilla_items.get(chapter, []))

        # Step 2: Apply unified (completely replaces per type)
        if chapter in self._unified:
            uni = self._unified[chapter]
            if "weapons" in uni:
                weapons = list(uni["weapons"])
            if "items" in uni:
                items = list(uni["items"])

        # Step 3: Apply difficulty override (replaces per type independently)
        if difficulty in self._overrides and chapter in self._overrides[difficulty]:
            ovr = self._overrides[difficulty][chapter]
            if "weapons" in ovr:
                weapons = list(ovr["weapons"])
            if "items" in ovr:
                items = list(ovr["items"])

        return {"weapons": weapons, "items": items}

    def to_dict(self) -> dict:
        """Serialize edits to JSON-compatible dict (for project file)."""
        result = {"unified": {}, "overrides": {}}
        for ch, data in self._unified.items():
            result["unified"][ch] = dict(data)
        for diff, chapters in self._overrides.items():
            result["overrides"][diff] = {}
            for ch, data in chapters.items():
                result["overrides"][diff][ch] = dict(data)
        return result

    def load_from_dict(self, d: dict):
        """Load edits from a JSON-compatible dict (from project file)."""
        self._unified = {}
        self._overrides = {}
        for ch, data in d.get("unified", {}).items():
            self._unified[ch] = dict(data)
        for diff, chapters in d.get("overrides", {}).items():
            self._overrides[diff] = {}
            for ch, data in chapters.items():
                self._overrides[diff][ch] = dict(data)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_shop_data.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/models/shop_data.py fe10_mod_editor/tests/test_shop_data.py
git commit -m "feat: add ShopDatabase with unified-with-overrides resolution"
```

---

## Task 11: Project File Model (`models/project.py`)

**Files:**
- Create: `fe10_mod_editor/models/project.py`
- Create: `fe10_mod_editor/tests/test_project.py`

Load/save `.fe10mod` JSON files. Manages paths, backup hashes, item edits, shop edits, and misc toggles.

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_project.py`:

```python
import json
import pytest
from fe10_mod_editor.models.project import ProjectFile


def test_project_new_creates_defaults():
    proj = ProjectFile.new()
    assert proj.version == 1
    assert proj.item_edits == {}
    assert proj.misc["weapon_changes"]["remove_prf_locks"] is False


def test_project_save_and_load(tmp_path):
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = "/some/backup"
    proj.item_edits["IID_IRON_SWORD"] = {"price": 0, "might": 12}
    proj.misc["weapon_changes"]["remove_prf_locks"] = True

    path = str(tmp_path / "test.fe10mod")
    proj.save(path)

    loaded = ProjectFile.load(path)
    assert loaded.paths["backup_dir"] == "/some/backup"
    assert loaded.item_edits["IID_IRON_SWORD"]["price"] == 0
    assert loaded.misc["weapon_changes"]["remove_prf_locks"] is True


def test_project_file_is_valid_json(tmp_path):
    proj = ProjectFile.new()
    path = str(tmp_path / "test.fe10mod")
    proj.save(path)

    with open(path) as f:
        data = json.load(f)
    assert data["version"] == 1
    assert "paths" in data
    assert "backup_hashes" in data


def test_project_shop_edits_roundtrip(tmp_path):
    proj = ProjectFile.new()
    proj.shop_edits = {
        "unified": {"C0101": {"weapons": ["IID_A"]}},
        "overrides": {"hard": {"C0101": {"weapons": ["IID_B"]}}},
    }

    path = str(tmp_path / "test.fe10mod")
    proj.save(path)
    loaded = ProjectFile.load(path)

    assert loaded.shop_edits["unified"]["C0101"]["weapons"] == ["IID_A"]
    assert loaded.shop_edits["overrides"]["hard"]["C0101"]["weapons"] == ["IID_B"]
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_project.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/models/project.py`:

```python
"""Project file (.fe10mod) management — load, save, validate.

The project file is a JSON document storing only diffs from original game data.
See the spec's Project File Format section for the full schema.
"""

import json


class ProjectFile:
    def __init__(self):
        self.version: int = 1
        self.paths: dict = {"backup_dir": "", "game_dir": ""}
        self.backup_hashes: dict[str, str] = {}
        self.item_edits: dict[str, dict] = {}
        self.shop_edits: dict = {"unified": {}, "overrides": {}}
        self.misc: dict = {
            "weapon_changes": {
                "remove_prf_locks": False,
                "remove_valuable": False,
                "remove_seal_steal": False,
            }
        }

    @classmethod
    def new(cls) -> "ProjectFile":
        return cls()

    def save(self, filepath: str):
        data = {
            "version": self.version,
            "paths": self.paths,
            "backup_hashes": self.backup_hashes,
            "item_edits": self.item_edits,
            "shop_edits": self.shop_edits,
            "misc": self.misc,
        }
        with open(filepath, "w") as f:
            json.dump(data, f, indent=2)

    @classmethod
    def load(cls, filepath: str) -> "ProjectFile":
        with open(filepath) as f:
            data = json.load(f)

        proj = cls()
        proj.version = data.get("version", 1)
        proj.paths = data.get("paths", proj.paths)
        proj.backup_hashes = data.get("backup_hashes", {})
        proj.item_edits = data.get("item_edits", {})
        proj.shop_edits = data.get("shop_edits", {"unified": {}, "overrides": {}})
        proj.misc = data.get("misc", proj.misc)
        return proj
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_project.py -v`
Expected: All 4 tests PASS

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/models/project.py fe10_mod_editor/tests/test_project.py
git commit -m "feat: add ProjectFile model for .fe10mod JSON load/save"
```

---

## Task 12: Build Pipeline (`models/mod_builder.py`)

**Files:**
- Create: `fe10_mod_editor/models/mod_builder.py`
- Create: `fe10_mod_editor/tests/test_mod_builder.py`

Orchestrates the full build: verify backups, decompress, apply item edits, apply misc toggles, recompress, rebuild shops, patch FST. Uses a callback for progress logging (the GUI will connect this to the build log widget).

- [ ] **Step 1: Write the failing tests**

Create `fe10_mod_editor/tests/test_mod_builder.py`:

```python
import os
import struct
import tempfile
import shutil
import pytest
from fe10_mod_editor.models.mod_builder import ModBuilder
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.core.backup_manager import compute_backup_hashes


@pytest.fixture
def build_env(backup_dir):
    """Create a temporary game directory structure for build testing."""
    tmp = tempfile.mkdtemp()
    game_files = os.path.join(tmp, "Game", "DATA", "files")
    shop_out = os.path.join(game_files, "Shop")
    sys_dir = os.path.join(tmp, "Game", "DATA", "sys")
    os.makedirs(shop_out)
    os.makedirs(sys_dir)

    # Copy backup files to game directory as starting state
    shutil.copy2(os.path.join(backup_dir, "FE10Data.cms"), game_files)
    for fname in ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]:
        shutil.copy2(os.path.join(backup_dir, fname), shop_out)
    shutil.copy2(os.path.join(backup_dir, "fst.bin"), sys_dir)

    yield {
        "tmp": tmp,
        "backup_dir": backup_dir,
        "game_files": game_files,
        "shop_dir": shop_out,
        "fst_path": os.path.join(sys_dir, "fst.bin"),
    }

    shutil.rmtree(tmp)


def test_mod_builder_runs_without_error(build_env):
    """Build with no edits should succeed (produces original-equivalent output)."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = build_env["backup_dir"]
    proj.paths["game_dir"] = os.path.join(build_env["tmp"], "Game", "DATA")
    proj.backup_hashes = compute_backup_hashes(build_env["backup_dir"])

    log_lines = []
    builder = ModBuilder(proj, log_callback=lambda msg: log_lines.append(msg))
    builder.build()

    assert len(log_lines) > 0
    assert any("complete" in line.lower() for line in log_lines)


def test_mod_builder_applies_price_edit(build_env):
    """Build with a price edit should produce modified FE10Data."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = build_env["backup_dir"]
    proj.paths["game_dir"] = os.path.join(build_env["tmp"], "Game", "DATA")
    proj.backup_hashes = compute_backup_hashes(build_env["backup_dir"])
    proj.item_edits["IID_IRON_SWORD"] = {"price": 0}

    builder = ModBuilder(proj, log_callback=lambda msg: None)
    builder.build()

    # Verify the output FE10Data.cms was written
    output_cms = os.path.join(build_env["game_files"], "FE10Data.cms")
    assert os.path.exists(output_cms)
    assert os.path.getsize(output_cms) > 0
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_mod_builder.py -v`
Expected: FAIL — module not found

- [ ] **Step 3: Write the implementation**

Create `fe10_mod_editor/models/mod_builder.py`:

```python
"""Build pipeline orchestration — applies all edits and produces modified game files.

Build steps (from spec):
1. Verify backup hashes
2. Decompress FE10Data.cms from backup
3. Apply item_edits to decompressed binary
4. Apply misc toggles (PRF removal, valuable removal, seal steal removal)
5. Recompress with LZ10, pad to original size
6. Rebuild shop files per difficulty using CompressShopfile
7. Update fst.bin with new file sizes
8. Write all output to game directory
"""

import os
import struct
from typing import Callable

from fe10_mod_editor.core.lz10 import decompress_lz10, compress_lz10
from fe10_mod_editor.core.cms_parser import resolve_string
from fe10_mod_editor.core.item_parser import parse_all_items, ITEM_DATA_OFFSET
from fe10_mod_editor.core.shop_parser import parse_shop_file
from fe10_mod_editor.core.shop_builder import build_shop_file
from fe10_mod_editor.core.fst_updater import patch_fst_sizes
from fe10_mod_editor.core.backup_manager import verify_backup_hashes
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.item_data import ItemDatabase
from fe10_mod_editor.models.shop_data import ShopDatabase

ORIGINAL_CMS_SIZE = 124288
DIFFICULTY_MAP = {"n": "normal", "m": "hard", "h": "maniac"}


class ModBuilder:
    def __init__(self, project: ProjectFile, log_callback: Callable[[str], None] | None = None):
        self.project = project
        self.log = log_callback or (lambda msg: None)

    def build(self):
        backup_dir = self.project.paths["backup_dir"]
        game_dir = self.project.paths["game_dir"]
        game_files = os.path.join(game_dir, "files")
        shop_out = os.path.join(game_files, "Shop")
        fst_path = os.path.join(game_dir, "sys", "fst.bin")

        # Step 1: Verify backups
        self.log("Verifying backup files...")
        result = verify_backup_hashes(backup_dir, self.project.backup_hashes)
        if not result.ok:
            raise RuntimeError(f"Backup verification failed: {result.error}")
        self.log("Backup files verified.")

        # Step 2: Decompress FE10Data from backup
        self.log("Decompressing FE10Data.cms...")
        cms_path = os.path.join(backup_dir, "FE10Data.cms")
        with open(cms_path, "rb") as f:
            compressed = f.read()
        data = bytearray(decompress_lz10(compressed))
        self.log(f"Decompressed: {len(data)} bytes")

        # Step 3: Apply item edits
        items = parse_all_items(bytes(data))
        edits = self.project.item_edits
        edit_count = 0

        for item in items:
            iid = item["iid"]
            if iid not in edits:
                continue
            item_edits = edits[iid]
            off = item["byte_offset"]

            field_offsets = {
                "price": (38, ">H"),
                "might": (40, "B"),
                "accuracy": (41, "B"),
                "critical": (42, "B"),
                "weight": (43, "B"),
                "uses": (44, "B"),
                "wexp_gain": (45, "B"),
            }

            for field_name, (field_off, fmt) in field_offsets.items():
                if field_name in item_edits:
                    struct.pack_into(fmt, data, off + field_off, item_edits[field_name])

            # Weapon rank edit
            if "weapon_rank" in item_edits:
                target_rank = item_edits["weapon_rank"]
                rank_ptr = self._find_rank_pointer(bytes(data), items, target_rank)
                if rank_ptr is not None:
                    struct.pack_into(">I", data, off + 20, rank_ptr)

            edit_count += 1
            self.log(f"  Edited: {iid}")

        self.log(f"Applied {edit_count} item edits.")

        # Step 4: Apply misc toggles
        self._apply_misc_toggles(data, items)

        # Step 5: Recompress
        self.log("Recompressing FE10Data.cms (this may take a while)...")
        recompressed = bytearray(compress_lz10(bytes(data)))
        if len(recompressed) <= ORIGINAL_CMS_SIZE:
            recompressed.extend(b"\x00" * (ORIGINAL_CMS_SIZE - len(recompressed)))
        else:
            self.log(f"WARNING: Recompressed size ({len(recompressed)}) exceeds original ({ORIGINAL_CMS_SIZE})")

        os.makedirs(game_files, exist_ok=True)
        with open(os.path.join(game_files, "FE10Data.cms"), "wb") as f:
            f.write(recompressed)
        self.log(f"Wrote FE10Data.cms ({len(recompressed)} bytes)")

        # Also write decompressed data (needed by shop builder)
        decomp_path = os.path.join(game_files, "FE10Data_decompressed.bin")
        with open(decomp_path, "wb") as f:
            f.write(data)

        # Step 6: Rebuild shop files
        self.log("Rebuilding shop files...")
        item_db = ItemDatabase.from_parsed_items(parse_all_items(bytes(data)))
        all_weapon_iids = [i.iid for i in item_db.weapon_shop_items]
        all_item_iids = [i.iid for i in item_db.item_shop_items]

        # Build ShopDatabase from vanilla + edits
        shop_db = ShopDatabase(vanilla_weapons={}, vanilla_items={})

        shop_sizes = {}
        os.makedirs(shop_out, exist_ok=True)

        for suffix, difficulty in DIFFICULTY_MAP.items():
            bak_shop = os.path.join(backup_dir, f"shopitem_{suffix}.bin")
            orig_info = parse_shop_file(bak_shop)

            # Build per-chapter item lists for this difficulty
            # For now, use the shop_edits from the project to determine inventory
            # Default: use all items (matching original mod behavior) unless project has specific edits
            per_chapter_weapons = {}
            per_chapter_items = {}

            from fe10_mod_editor.core.shop_parser import CHAPTERS
            for ch in CHAPTERS:
                # Resolve what this chapter should stock
                ch_weapons = list(all_weapon_iids)  # default: all
                ch_items = list(all_item_iids)       # default: all

                # Apply unified edits
                unified = self.project.shop_edits.get("unified", {})
                if ch in unified:
                    if "weapons" in unified[ch]:
                        ch_weapons = unified[ch]["weapons"]
                    if "items" in unified[ch]:
                        ch_items = unified[ch]["items"]

                # Apply difficulty overrides
                overrides = self.project.shop_edits.get("overrides", {})
                if difficulty in overrides and ch in overrides[difficulty]:
                    ovr = overrides[difficulty][ch]
                    if "weapons" in ovr:
                        ch_weapons = ovr["weapons"]
                    if "items" in ovr:
                        ch_items = ovr["items"]

                per_chapter_weapons[ch] = ch_weapons
                per_chapter_items[ch] = ch_items

            # Pass per-chapter item dicts to the shop builder
            result = build_shop_file(orig_info, per_chapter_weapons, per_chapter_items)

            out_path = os.path.join(shop_out, f"shopitem_{suffix}.bin")
            with open(out_path, "wb") as f:
                f.write(result)
            shop_sizes[f"shopitem_{suffix}.bin"] = len(result)
            self.log(f"  shopitem_{suffix}.bin: {len(result)} bytes")

        self.log("Shop files rebuilt.")

        # Step 7: Update FST
        self.log("Updating fst.bin...")
        with open(os.path.join(backup_dir, "fst.bin"), "rb") as f:
            fst_data = f.read()

        patched_fst = patch_fst_sizes(fst_data, shop_sizes)
        os.makedirs(os.path.dirname(fst_path), exist_ok=True)
        with open(fst_path, "wb") as f:
            f.write(patched_fst)
        self.log("FST updated.")

        self.log("Build complete!")

    def _find_rank_pointer(self, data: bytes, items: list[dict], target_rank: str) -> int | None:
        """Find the pointer value for a given rank string by scanning items."""
        for item in items:
            rank_ptr = item["_rank_ptr"]
            rank_str = resolve_string(data, rank_ptr)
            if rank_str == target_rank:
                return rank_ptr
        return None

    def _apply_misc_toggles(self, data: bytearray, items: list[dict]):
        """Apply batch misc toggles to the decompressed data."""
        misc = self.project.misc.get("weapon_changes", {})

        # Find rank D pointer for PRF lock removal
        rank_d_ptr = self._find_rank_pointer(bytes(data), items, "D")

        for item in items:
            off = item["byte_offset"]
            ac = data[off + 53]

            # Remove PRF locks
            if misc.get("remove_prf_locks", False):
                rank_ptr = struct.unpack(">I", data[off + 20:off + 24])[0]
                rank_str = resolve_string(bytes(data), rank_ptr)
                if rank_str == "N" and rank_d_ptr is not None:
                    struct.pack_into(">I", data, off + 20, rank_d_ptr)
                    self.log(f"  PRF removed: {item['iid']}")

                # Remove eq* attributes
                for a in range(ac):
                    attr_off = off + 56 + a * 4
                    attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
                    attr_str = resolve_string(bytes(data), attr_ptr)
                    if attr_str and attr_str.startswith("eq"):
                        struct.pack_into(">I", data, attr_off, 0)

            # Remove valuable flag
            if misc.get("remove_valuable", False):
                for a in range(ac):
                    attr_off = off + 56 + a * 4
                    attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
                    attr_str = resolve_string(bytes(data), attr_ptr)
                    if attr_str == "valuable":
                        struct.pack_into(">I", data, attr_off, 0)

            # Remove seal steal
            if misc.get("remove_seal_steal", False):
                for a in range(ac):
                    attr_off = off + 56 + a * 4
                    attr_ptr = struct.unpack(">I", data[attr_off:attr_off + 4])[0]
                    attr_str = resolve_string(bytes(data), attr_ptr)
                    if attr_str == "sealsteal":
                        struct.pack_into(">I", data, attr_off, 0)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_mod_builder.py -v`
Expected: All 2 tests PASS (may be slow due to LZ10 compression)

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/models/mod_builder.py fe10_mod_editor/tests/test_mod_builder.py
git commit -m "feat: add ModBuilder pipeline with item edits, misc toggles, and shop rebuild"
```

---

## Task 13: Main Window Shell (`views/main_window.py`, `main.py`)

**Files:**
- Create: `fe10_mod_editor/main.py`
- Create: `fe10_mod_editor/views/main_window.py`

Minimal window with tab bar (Items/Shops/Build/Misc), menu bar, toolbar, and status bar. Tabs show placeholder content initially. File > New/Open/Save project actions.

- [ ] **Step 1: Write the implementation**

No TDD for UI shell — verify by launching the app manually.

Create `fe10_mod_editor/views/main_window.py`:

```python
"""Main application window with tab bar, menu bar, toolbar, and status bar."""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QStatusBar, QToolBar, QMenuBar,
    QFileDialog, QWidget, QLabel, QVBoxLayout,
)
from PySide6.QtCore import Qt
from PySide6.QtGui import QAction
from fe10_mod_editor.models.project import ProjectFile


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("FE10 Mod Editor")
        self.setMinimumSize(1200, 800)

        self.project = ProjectFile.new()
        self.project_path: str | None = None

        self._setup_menu_bar()
        self._setup_toolbar()
        self._setup_tabs()
        self._setup_status_bar()

    def _setup_menu_bar(self):
        menu_bar = self.menuBar()

        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self._new_project)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self._open_project)
        file_menu.addAction(open_action)

        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self._save_project)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self._save_project_as)
        file_menu.addAction(save_as_action)

        # Stub menus for future features
        menu_bar.addMenu("&Edit")
        menu_bar.addMenu("&Tools")
        menu_bar.addMenu("&Help")

    def _setup_toolbar(self):
        toolbar = QToolBar("Main Toolbar")
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_btn = QAction("Open Project", self)
        open_btn.triggered.connect(self._open_project)
        toolbar.addAction(open_btn)

        save_btn = QAction("Save", self)
        save_btn.triggered.connect(self._save_project)
        toolbar.addAction(save_btn)

        toolbar.addSeparator()
        self._project_label = QLabel("No project loaded")
        toolbar.addWidget(self._project_label)

    def _setup_tabs(self):
        self.tabs = QTabWidget()
        self.setCentralWidget(self.tabs)

        # Placeholder tabs — will be replaced by real views in later tasks
        for name in ["Items", "Shops", "Build", "Misc"]:
            placeholder = QWidget()
            layout = QVBoxLayout(placeholder)
            layout.addWidget(QLabel(f"{name} tab — coming soon"))
            self.tabs.addTab(placeholder, name)

    def _setup_status_bar(self):
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _new_project(self):
        self.project = ProjectFile.new()
        self.project_path = None
        self._project_label.setText("New project (unsaved)")
        self.status_bar.showMessage("New project created")

    def _open_project(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "Open Project", "", "FE10 Mod Files (*.fe10mod);;All Files (*)"
        )
        if path:
            self.project = ProjectFile.load(path)
            self.project_path = path
            self._project_label.setText(path.split("/")[-1].split("\\")[-1])
            self.status_bar.showMessage(f"Loaded: {path}")

    def _save_project(self):
        if self.project_path:
            self.project.save(self.project_path)
            self.status_bar.showMessage(f"Saved: {self.project_path}")
        else:
            self._save_project_as()

    def _save_project_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "Save Project", "", "FE10 Mod Files (*.fe10mod);;All Files (*)"
        )
        if path:
            self.project.save(path)
            self.project_path = path
            self._project_label.setText(path.split("/")[-1].split("\\")[-1])
            self.status_bar.showMessage(f"Saved: {path}")
```

Create `fe10_mod_editor/main.py`:

```python
"""Entry point for the FE10 Mod Editor GUI application."""

import sys
from PySide6.QtWidgets import QApplication
from fe10_mod_editor.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
```

- [ ] **Step 2: Verify by launching**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m fe10_mod_editor.main`
Expected: Window opens with 4 placeholder tabs, menu bar, toolbar, status bar. Close to exit.

- [ ] **Step 3: Commit**

```bash
git add fe10_mod_editor/main.py fe10_mod_editor/views/main_window.py
git commit -m "feat: add main window shell with tab bar, menu, toolbar, and status bar"
```

---

## Task 14: Toggle Card Widget + Misc Tab (`widgets/toggle_card.py`, `views/misc_tab.py`)

**Files:**
- Create: `fe10_mod_editor/widgets/toggle_card.py`
- Create: `fe10_mod_editor/views/misc_tab.py`
- Modify: `fe10_mod_editor/views/main_window.py` — replace Misc placeholder tab

The Misc tab is the simplest real tab — just toggle cards in categories. Good to build first as it exercises the widget → view → project data flow without complex table widgets.

- [ ] **Step 1: Write ToggleCard widget**

Create `fe10_mod_editor/widgets/toggle_card.py`:

```python
"""Toggle card widget — a labeled on/off switch with description and affected count."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
from PySide6.QtCore import Signal


class ToggleCard(QFrame):
    toggled = Signal(str, bool)  # (toggle_key, new_state)

    def __init__(self, key: str, title: str, description: str, affected_count: int, parent=None):
        super().__init__(parent)
        self.key = key
        self.setFrameStyle(QFrame.Box | QFrame.Plain)

        layout = QHBoxLayout(self)

        text_layout = QVBoxLayout()
        title_label = QLabel(f"<b>{title}</b>")
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        self.count_label = QLabel(f"Affects {affected_count} items")
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        text_layout.addWidget(self.count_label)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_toggle)

        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(self.checkbox)

    def _on_toggle(self, state):
        self.toggled.emit(self.key, self.checkbox.isChecked())

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)
```

- [ ] **Step 2: Write MiscTab view**

Create `fe10_mod_editor/views/misc_tab.py`:

```python
"""Misc tab — batch toggle operations organized by category."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from fe10_mod_editor.widgets.toggle_card import ToggleCard

WEAPON_CHANGES = [
    {
        "key": "remove_prf_locks",
        "title": "Remove PRF Locks",
        "description": "Changes weapon rank from N (personal) to D on all PRF weapons, "
                       "removes equip-lock attributes. Allows any character to equip "
                       "previously locked weapons like Ragnell, Alondite, etc.",
        "count": 18,
    },
    {
        "key": "remove_valuable",
        "title": "Remove Valuable Flag",
        "description": "Removes the 'valuable' attribute from all items. "
                       "Valuable items cannot be discarded or sold.",
        "count": 34,
    },
    {
        "key": "remove_seal_steal",
        "title": "Remove Steal Protection",
        "description": "Removes the 'sealsteal' attribute from all items. "
                       "Makes all items stealable.",
        "count": 9,
    },
]


class MiscTab(QWidget):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self._cards: dict[str, ToggleCard] = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # Weapon Changes category
        header = QLabel("<h2>Weapon Changes</h2>")
        layout.addWidget(header)

        for toggle_def in WEAPON_CHANGES:
            card = ToggleCard(
                key=toggle_def["key"],
                title=toggle_def["title"],
                description=toggle_def["description"],
                affected_count=toggle_def["count"],
            )
            card.toggled.connect(self._on_toggle)
            layout.addWidget(card)
            self._cards[toggle_def["key"]] = card

        layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        self._sync_from_project()

    def _sync_from_project(self):
        wc = self.project.misc.get("weapon_changes", {})
        for key, card in self._cards.items():
            card.set_checked(wc.get(key, False))

    def _on_toggle(self, key: str, checked: bool):
        self.project.misc.setdefault("weapon_changes", {})[key] = checked
```

- [ ] **Step 3: Wire MiscTab into MainWindow**

In `main_window.py`, import `MiscTab` and replace the Misc placeholder tab with the real one. Pass `self.project` to `MiscTab(self.project)`.

- [ ] **Step 4: Verify by launching**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m fe10_mod_editor.main`
Expected: Misc tab shows 3 toggle cards under "Weapon Changes" heading. Toggling them updates project state.

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/widgets/toggle_card.py fe10_mod_editor/views/misc_tab.py fe10_mod_editor/views/main_window.py
git commit -m "feat: add Misc tab with toggle cards for batch weapon changes"
```

---

## Task 15: Item Table Widget + Items Tab (`widgets/item_table.py`, `widgets/item_editor.py`, `views/items_tab.py`)

**Files:**
- Create: `fe10_mod_editor/widgets/item_table.py`
- Create: `fe10_mod_editor/widgets/item_editor.py`
- Create: `fe10_mod_editor/views/items_tab.py`
- Modify: `fe10_mod_editor/views/main_window.py` — replace Items placeholder tab

This is the most complex UI task. The item table shows all 296 items with filtering/sorting. The side panel editor shows editable fields for the selected item.

- [ ] **Step 1: Write ItemTableModel and ItemTableWidget**

Create `fe10_mod_editor/widgets/item_table.py`. Use `QAbstractTableModel` for the data model with a `QSortFilterProxyModel` for filtering. Columns: Name, Type, Rank, Mt, Hit, Crt, Wt, Uses, Price, PRF.

The model takes an `ItemDatabase` reference and a dict of `item_edits` from the project. Modified values are read from `item_edits` overlay; unmodified values come from the `ItemDatabase`.

Include filter methods: `set_type_filter(weapon_type: str | None)` and `set_search_text(text: str)`.

- [ ] **Step 2: Write ItemEditor side panel**

Create `fe10_mod_editor/widgets/item_editor.py`. A `QWidget` with grouped `QSpinBox` fields for combat stats (Might, Accuracy, Critical, Weight, Uses, WExp Gain), price, and a rank dropdown. Read-only labels for weapon type and IID. "Reset to Original" button.

The editor emits a `field_changed(iid: str, field: str, value: int)` signal when any field is edited. Soft guardrails: set `QSpinBox` palette to yellow when value exceeds vanilla range for that weapon type.

- [ ] **Step 3: Write ItemsTab view**

Create `fe10_mod_editor/views/items_tab.py`. `QSplitter` layout with `ItemTableWidget` on the left and `ItemEditor` on the right. Filter bar above the table with a search `QLineEdit` and type filter buttons. Connects table selection to editor population. Connects editor changes to project `item_edits`.

- [ ] **Step 4: Wire ItemsTab into MainWindow**

In `main_window.py`, replace the Items placeholder. The Items tab needs the project (for edits) and will load the `ItemDatabase` when a project is opened (backup_dir points to the game files).

Add a `_load_item_database()` method to `MainWindow` that decompresses FE10Data and builds an `ItemDatabase`. Call it when a project is opened.

- [ ] **Step 5: Verify by launching**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m fe10_mod_editor.main`
Expected: After opening a project (with valid backup_dir), the Items tab shows all 296 items in a sortable/filterable table. Clicking an item shows its stats in the side panel. Editing stats updates the project.

- [ ] **Step 6: Commit**

```bash
git add fe10_mod_editor/widgets/item_table.py fe10_mod_editor/widgets/item_editor.py fe10_mod_editor/views/items_tab.py fe10_mod_editor/views/main_window.py
git commit -m "feat: add Items tab with filterable table and side panel editor"
```

---

## Task 16: Shop Inventory Widget + Shops Tab (`widgets/shop_inventory.py`, `views/shops_tab.py`)

**Files:**
- Create: `fe10_mod_editor/widgets/shop_inventory.py`
- Create: `fe10_mod_editor/views/shops_tab.py`
- Modify: `fe10_mod_editor/views/main_window.py` — replace Shops placeholder tab

- [ ] **Step 1: Write ShopInventoryWidget**

Create `fe10_mod_editor/widgets/shop_inventory.py`. A `QWidget` with a `QListWidget` (or `QTableWidget`) showing items with checkboxes. Checked = in stock. Has "Stock All" and "Clear" buttons. Counter label ("X / N items stocked"). Emits `inventory_changed(list[str])` signal with current checked IIDs.

- [ ] **Step 2: Write ShopsTab view**

Create `fe10_mod_editor/views/shops_tab.py`. Three-zone layout:
- Left: `QTreeWidget` for chapter list, grouped by Part headers
- Center: Two `ShopInventoryWidget`s side by side (weapons + items)
- Top bar: difficulty selector buttons (All / Normal / Hard / Maniac)

When a chapter is selected, populate the two inventory widgets with the resolved inventory from `ShopDatabase.resolve()`. When inventory changes, update the project's `shop_edits`.

Handle chapters with no original shop: show as grayed in the chapter list, but allow adding items.

- [ ] **Step 3: Wire ShopsTab into MainWindow**

Replace the Shops placeholder. Load `ShopDatabase` from parsed shop files when a project is opened.

- [ ] **Step 4: Verify by launching**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m fe10_mod_editor.main`
Expected: Shops tab shows chapter list on left, two inventory panels in center. Selecting a chapter populates inventories. Stock All/Clear buttons work. Difficulty switching works.

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/widgets/shop_inventory.py fe10_mod_editor/views/shops_tab.py fe10_mod_editor/views/main_window.py
git commit -m "feat: add Shops tab with chapter list and two-column inventory editor"
```

---

## Task 17: Build Tab (`views/build_tab.py`)

**Files:**
- Create: `fe10_mod_editor/views/build_tab.py`
- Modify: `fe10_mod_editor/views/main_window.py` — replace Build placeholder tab

- [ ] **Step 1: Write BuildTab view**

Create `fe10_mod_editor/views/build_tab.py`. Two-column layout:
- Left: Path settings (backup_dir, game_dir with Browse buttons), change summary counts, "Build Mod" button, "Restore Original Files" button (in a danger zone section with confirmation dialog)
- Right: `QPlainTextEdit` (read-only) for build log output

The Build button creates a `QThread` worker that runs `ModBuilder.build()`, forwarding log messages to the text edit via signals. Build button disabled during build.

Path Browse buttons open `QFileDialog.getExistingDirectory()` and update the project. Backup validation runs when backup_dir changes, showing a green/red indicator.

- [ ] **Step 2: Wire BuildTab into MainWindow**

Replace the Build placeholder. Pass the project reference.

- [ ] **Step 3: Verify by launching**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m fe10_mod_editor.main`
Expected: Build tab shows path settings, build button, and log panel. Setting paths and clicking Build runs the pipeline with log output. Restore button shows confirmation dialog.

- [ ] **Step 4: Commit**

```bash
git add fe10_mod_editor/views/build_tab.py fe10_mod_editor/views/main_window.py
git commit -m "feat: add Build tab with threaded build pipeline and log output"
```

---

## Task 18: Integration Test — Full Roundtrip

**Files:**
- Create: `fe10_mod_editor/tests/test_integration.py`

End-to-end test: create a project, set some item edits and misc toggles, build, and verify the output files are valid.

- [ ] **Step 1: Write integration test**

Create `fe10_mod_editor/tests/test_integration.py`:

```python
import os
import tempfile
import shutil
import pytest
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.mod_builder import ModBuilder
from fe10_mod_editor.core.backup_manager import compute_backup_hashes
from fe10_mod_editor.core.lz10 import decompress_lz10
from fe10_mod_editor.core.item_parser import parse_all_items
from fe10_mod_editor.core.shop_parser import parse_shop_file
from fe10_mod_editor.core.cms_parser import parse_cms_header


@pytest.fixture
def full_build_env(backup_dir):
    """Set up a complete build environment."""
    tmp = tempfile.mkdtemp()
    game_dir = os.path.join(tmp, "Game", "DATA")
    game_files = os.path.join(game_dir, "files")
    shop_out = os.path.join(game_files, "Shop")
    sys_dir = os.path.join(game_dir, "sys")
    os.makedirs(shop_out)
    os.makedirs(sys_dir)

    # Copy originals to game directory
    shutil.copy2(os.path.join(backup_dir, "FE10Data.cms"), game_files)
    for f in ["shopitem_n.bin", "shopitem_m.bin", "shopitem_h.bin"]:
        shutil.copy2(os.path.join(backup_dir, f), shop_out)
    shutil.copy2(os.path.join(backup_dir, "fst.bin"), sys_dir)

    yield {"tmp": tmp, "backup_dir": backup_dir, "game_dir": game_dir}
    shutil.rmtree(tmp)


def test_full_roundtrip_with_edits(full_build_env):
    """Build a mod with price edits and PRF removal, verify output is valid."""
    proj = ProjectFile.new()
    proj.paths["backup_dir"] = full_build_env["backup_dir"]
    proj.paths["game_dir"] = full_build_env["game_dir"]
    proj.backup_hashes = compute_backup_hashes(full_build_env["backup_dir"])

    # Edit Iron Sword price to 0
    proj.item_edits["IID_IRON_SWORD"] = {"price": 0}
    # Enable PRF lock removal
    proj.misc["weapon_changes"]["remove_prf_locks"] = True

    log = []
    builder = ModBuilder(proj, log_callback=lambda msg: log.append(msg))
    builder.build()

    # Verify FE10Data.cms was produced
    cms_path = os.path.join(full_build_env["game_dir"], "files", "FE10Data.cms")
    assert os.path.exists(cms_path)

    # Verify shop files were produced and are valid CMS
    for suffix in ["n", "m", "h"]:
        shop_path = os.path.join(full_build_env["game_dir"], "files", "Shop", f"shopitem_{suffix}.bin")
        assert os.path.exists(shop_path)
        with open(shop_path, "rb") as f:
            shop_data = f.read()
        header = parse_cms_header(shop_data)
        assert header["file_size"] == len(shop_data)

    # Verify fst.bin was updated
    fst_path = os.path.join(full_build_env["game_dir"], "sys", "fst.bin")
    assert os.path.exists(fst_path)

    # Verify the price edit was applied
    with open(cms_path, "rb") as f:
        modded_cms = f.read()
    modded_data = decompress_lz10(modded_cms)
    items = parse_all_items(modded_data)
    iron_sword = next(i for i in items if i["iid"] == "IID_IRON_SWORD")
    assert iron_sword["price"] == 0

    # Verify build log has completion message
    assert any("complete" in line.lower() for line in log)
```

- [ ] **Step 2: Run integration test**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m pytest fe10_mod_editor/tests/test_integration.py -v --timeout=300`
Expected: PASS (may take a few minutes due to LZ10 compression)

- [ ] **Step 3: Commit**

```bash
git add fe10_mod_editor/tests/test_integration.py
git commit -m "test: add full roundtrip integration test for build pipeline"
```

---

## Task 19: Polish and Final Wiring

**Files:**
- Modify: `fe10_mod_editor/views/main_window.py` — finalize all tab wiring, data loading on project open
- Modify: `fe10_mod_editor/views/items_tab.py` — connect modified-item highlighting
- Modify: `fe10_mod_editor/views/build_tab.py` — connect change summary counts

- [ ] **Step 1: Finalize MainWindow data loading**

When a project is opened, `MainWindow` should:
1. Load the project file
2. Verify backup hashes (show error dialog if failed)
3. Decompress FE10Data.cms from backup and build `ItemDatabase`
4. Parse all 3 shop files from backup and build `ShopDatabase`
5. Load shop edits from project into `ShopDatabase`
6. Refresh all tabs with the loaded data

- [ ] **Step 2: Connect change summary in Build tab**

The Build tab's change summary should dynamically count:
- Items modified: `len(project.item_edits)`
- Shops customized: count of chapters in `project.shop_edits.unified`
- Difficulty overrides: count across all difficulties in `project.shop_edits.overrides`
- Misc toggles active: count of True values in `project.misc.weapon_changes`

- [ ] **Step 3: Add modified-item highlighting in Items tab**

Items with entries in `project.item_edits` should be visually distinguished in the table (e.g., bold font or background color).

- [ ] **Step 4: Full manual test**

Run: `cd "C:/Users/miche/Documents/Programming/Fire Emblem - Radiant Dawn Claude Mod" && python -m fe10_mod_editor.main`

Test workflow:
1. File > New Project
2. Go to Build tab, set Backup and Game directory paths
3. Go to Items tab — verify 296 items load
4. Edit Iron Sword price to 0
5. Go to Shops tab — verify chapter list and inventories
6. Go to Misc tab — toggle PRF removal
7. File > Save As (save .fe10mod file)
8. Go to Build tab — click Build — verify log output shows success
9. File > Open — reopen the saved project — verify edits are restored

- [ ] **Step 5: Commit**

```bash
git add fe10_mod_editor/
git commit -m "feat: finalize tab wiring, data loading, and change summary"
```

---

## Summary

| Task | Component | Estimated Complexity |
|------|-----------|---------------------|
| 1 | Scaffolding | Low |
| 2 | LZ10 compression | Low (copy from existing) |
| 3 | CMS parser | Low |
| 4 | Item parser | Medium |
| 5 | Shop parser | Medium (complex binary format) |
| 6 | Shop builder | Medium (copy from existing) |
| 7 | FST updater | Low |
| 8 | Backup manager | Low |
| 9 | Item data model | Low |
| 10 | Shop data model | Medium |
| 11 | Project file model | Low |
| 12 | Build pipeline | High (orchestrates all core modules) |
| 13 | Main window shell | Low |
| 14 | Misc tab + toggle cards | Low |
| 15 | Items tab (table + editor) | High (most complex UI) |
| 16 | Shops tab | High (three-zone layout with complex state) |
| 17 | Build tab | Medium (threading) |
| 18 | Integration test | Medium |
| 19 | Polish + final wiring | Medium |

Tasks 1-12 are the core/model layer (no UI). Tasks 13-17 are the UI layer. Task 18-19 are integration and polish. The core layer can be built and tested entirely without PySide6 (except for the QThread in ModBuilder, which can be tested with the plain `build()` method).
