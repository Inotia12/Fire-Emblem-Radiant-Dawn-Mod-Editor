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
    assert "chapters" in result
    assert "tutorials" in result


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
