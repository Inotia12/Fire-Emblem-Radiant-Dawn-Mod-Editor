"""Class data model — wraps parsed class (job) data with display logic."""

from dataclasses import dataclass, field


def display_name_from_jid(jid: str) -> str:
    """Convert JID to display name: strip 'JID_', replace '_' with ' ', title case."""
    name = jid
    if name.startswith("JID_"):
        name = name[4:]
    return name.replace("_", " ").title()


@dataclass
class ClassEntry:
    jid: str
    mjid: str
    weapon_ranks: str
    constitution: int
    skill_capacity: int
    default_movement: int
    max_stats: dict = field(default_factory=dict)
    base_stats: dict = field(default_factory=dict)
    class_growth_rates: dict = field(default_factory=dict)
    max_stats_offset: int = 0
    byte_offset: int = 0
    promote_level: int = 0

    @property
    def display_name(self) -> str:
        return display_name_from_jid(self.jid)


class ClassDatabase:
    def __init__(self, classes: list[ClassEntry]):
        self._classes = classes
        self._by_jid = {c.jid: c for c in classes}

    @classmethod
    def from_parsed(cls, parsed: list[dict]) -> "ClassDatabase":
        """Build a ClassDatabase from a list of dicts returned by parse_all_classes."""
        entries = [
            ClassEntry(
                jid=p["jid"],
                mjid=p.get("mjid", ""),
                weapon_ranks=p.get("weapon_ranks", ""),
                constitution=p.get("constitution", 0),
                skill_capacity=p.get("skill_capacity", 0),
                default_movement=p.get("default_movement", 0),
                max_stats=p.get("max_stats", {}),
                base_stats=p.get("base_stats", {}),
                class_growth_rates=p.get("class_growth_rates", {}),
                max_stats_offset=p.get("max_stats_offset", 0),
                byte_offset=p.get("byte_offset", 0),
                promote_level=p.get("promote_level", 0),
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
