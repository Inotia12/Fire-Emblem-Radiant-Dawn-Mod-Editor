import struct
import pytest
from fe10_mod_editor.core.fst_updater import patch_fst_sizes, FST_SHOP_INDICES


def test_patch_fst_sizes_updates_entries():
    """Patching FST data updates the size fields at correct offsets."""
    max_index = max(FST_SHOP_INDICES.values())
    fst_size = (max_index + 1) * 12
    fst_data = bytearray(fst_size)

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

    struct.pack_into(">I", fst_data, 8, 0xDEADBEEF)

    new_sizes = {
        "shopitem_h.bin": 100,
        "shopitem_m.bin": 200,
        "shopitem_n.bin": 300,
    }

    patched = patch_fst_sizes(bytes(fst_data), new_sizes)
    sentinel = struct.unpack(">I", patched[8:12])[0]
    assert sentinel == 0xDEADBEEF
