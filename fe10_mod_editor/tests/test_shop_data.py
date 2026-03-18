import pytest
from fe10_mod_editor.models.shop_data import ShopDatabase


def test_shop_database_resolve_unified():
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A", "IID_B"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    db.set_unified("C0101", weapons=["IID_X", "IID_Y", "IID_Z"])
    resolved = db.resolve("C0101", "normal")
    assert resolved["weapons"] == ["IID_X", "IID_Y", "IID_Z"]
    assert resolved["items"] == ["IID_V"]


def test_shop_database_resolve_override_replaces_per_type():
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    db.set_unified("C0101", weapons=["IID_X", "IID_Y"], items=["IID_W"])
    db.set_override("C0101", "hard", weapons=["IID_Z"])

    resolved_hard = db.resolve("C0101", "hard")
    assert resolved_hard["weapons"] == ["IID_Z"]
    assert resolved_hard["items"] == ["IID_W"]

    resolved_normal = db.resolve("C0101", "normal")
    assert resolved_normal["weapons"] == ["IID_X", "IID_Y"]


def test_shop_database_resolve_vanilla_fallback():
    db = ShopDatabase(
        vanilla_weapons={"C0101": ["IID_A", "IID_B"]},
        vanilla_items={"C0101": ["IID_V"]},
    )
    resolved = db.resolve("C0101", "normal")
    assert resolved["weapons"] == ["IID_A", "IID_B"]
    assert resolved["items"] == ["IID_V"]


def test_shop_database_to_dict_and_from_dict():
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
