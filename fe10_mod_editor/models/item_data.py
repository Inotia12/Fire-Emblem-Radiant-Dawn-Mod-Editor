"""Item data model — wraps parsed item data with display logic and filtering."""

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
    display_type: str  # offset +12, used for shop classification
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
