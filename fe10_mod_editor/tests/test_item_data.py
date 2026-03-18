import pytest
from fe10_mod_editor.models.item_data import ItemEntry, ItemDatabase, display_name_from_iid


def test_display_name_from_iid():
    assert display_name_from_iid("IID_IRONSWORD") == "Ironsword"
    assert display_name_from_iid("IID_VULNERARY") == "Vulnerary"
    assert display_name_from_iid("IID_STEEL_BOW") == "Steel Bow"


def test_item_entry_creation():
    item = ItemEntry(
        iid="IID_IRONSWORD", display_type="sword", weapon_type="sword", weapon_rank="E",
        price=560, might=5, accuracy=100, critical=0, weight=5,
        uses=45, wexp_gain=2, min_range=1, max_range=1,
        attributes=[], effectiveness_count=0, prf_flag=0,
        icon_id=0, byte_offset=0,
    )
    assert item.display_name == "Ironsword"
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
    assert db.get("IID_IRONSWORD") is not None


def test_item_database_filter_by_type(backup_dir):
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
