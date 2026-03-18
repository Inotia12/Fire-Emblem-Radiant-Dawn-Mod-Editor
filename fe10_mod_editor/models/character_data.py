"""Character data model — wraps parsed character data with display logic and filtering."""

from dataclasses import dataclass, field


# Hardcoded list of all known playable character PIDs in FE10 Radiant Dawn.
# These are the characters the player can actually deploy on the map.
# The "playability_flag" field is not reliable for this — it stores the laguz
# transform threshold (0/3/7/15/31) and is unrelated to playability.
ALLIED_PIDS = frozenset({
    # Part 1 — Dawn Brigade / Micaiah's army
    "PID_MICAIAH", "PID_SOTHE", "PID_LAURA", "PID_EDDIE", "PID_NOLAN",
    "PID_MEG", "PID_VIKA", "PID_WAYU", "PID_TANIS", "PID_ZIHARK",
    "PID_MUSTON", "PID_MARJO", "PID_JILL", "PID_FIONA", "PID_TORMOD",
    "PID_PELLEAS", "PID_BRAD", "PID_LEONARDO",
    # Part 2 — Crimean Royal Knights / Elincia's army
    "PID_NEPHENEE", "PID_HEATHER", "PID_BROM", "PID_LEARNE", "PID_CALILL",
    "PID_HAAR", "PID_MARCIA", "PID_SIGRUN", "PID_ELAICE", "PID_ELNA",
    "PID_TAURONEO",
    # Part 3 — Greil Mercenaries / Ike's army
    "PID_IKE", "PID_TITANIA", "PID_SENERIO", "PID_OSCAR", "PID_BOYD",
    "PID_ROLF", "PID_GATRIE", "PID_NOSE", "PID_MIST", "PID_JANAFF",
    "PID_ULKI", "PID_VOLKE", "PID_STEFAN", "PID_NAESALA", "PID_NEALUCHI",
    "PID_GEOFFRAY", "PID_IZCA", "PID_LUCHINO",
    # Part 4 / Endgame additions
    "PID_TIBARN", "PID_CAINEGHIS", "PID_GIFFCA", "PID_SKRIMIR",
    "PID_RAFIEL", "PID_REYSON", "PID_LEANNE", "PID_SANAKI", "PID_KURTHNAGA",
    "PID_ENA", "PID_NASIR", "PID_OLIVER", "PID_ASTARTE", "PID_DHEGINHANSEA",
})


def display_name_from_pid(pid: str) -> str:
    """Convert PID to display name: strip 'PID_', replace '_' with ' ', title case."""
    name = pid
    if name.startswith("PID_"):
        name = name[4:]
    return name.replace("_", " ").title()


@dataclass
class CharacterEntry:
    pid: str
    mpid: str
    jid: str
    level: int
    gender: int
    skill_count: int
    skill_ids: list = field(default_factory=list)
    skill_slot_offsets: list = field(default_factory=list)
    biorhythm_type: int = 0
    playability_flag: int = 0  # Actually the laguz transform threshold, not playability
    authority_stars: int = 0
    laguz_gauge: dict = field(default_factory=dict)
    stat_adjustments: dict = field(default_factory=dict)
    growth_rates: dict = field(default_factory=dict)
    byte_offset: int = 0
    affinity: str = ""
    fid: str = ""

    @property
    def display_name(self) -> str:
        return display_name_from_pid(self.pid)

    @property
    def is_laguz(self) -> bool:
        g = self.laguz_gauge
        return any(g.get(k, 0) != 0 for k in ["gain_turn", "gain_battle", "loss_turn", "loss_battle"])


class CharacterDatabase:
    def __init__(self, characters: list[CharacterEntry]):
        self._characters = characters
        self._by_pid = {c.pid: c for c in characters}

    @classmethod
    def from_parsed(cls, parsed: list[dict]) -> "CharacterDatabase":
        """Build a CharacterDatabase from a list of dicts returned by parse_all_characters."""
        entries = [
            CharacterEntry(
                pid=p["pid"],
                mpid=p["mpid"],
                jid=p["jid"],
                level=p["level"],
                gender=p["gender"],
                skill_count=p["skill_count"],
                skill_ids=p.get("skill_ids", []),
                skill_slot_offsets=p.get("skill_slot_offsets", []),
                biorhythm_type=p.get("biorhythm_type", 0),
                playability_flag=p.get("playability_flag", 0),
                authority_stars=p.get("authority_stars", 0),
                laguz_gauge=p.get("laguz_gauge", {}),
                stat_adjustments=p.get("stat_adjustments", {}),
                growth_rates=p.get("growth_rates", {}),
                byte_offset=p.get("byte_offset", 0),
                affinity=p.get("affinity", ""),
                fid=p.get("fid", ""),
            )
            for p in parsed
        ]
        return cls(entries)

    @property
    def count(self) -> int:
        return len(self._characters)

    @property
    def all_characters(self) -> list[CharacterEntry]:
        return list(self._characters)

    @property
    def allied_characters(self) -> list[CharacterEntry]:
        """Return the known playable/allied characters using a hardcoded PID list.

        The 'playability_flag' field does NOT identify playable characters — it stores
        the laguz transform gauge threshold (0/3/7/15/31). Instead, we use ALLIED_PIDS,
        a curated set of the ~73 characters the player can actually deploy.
        """
        return [c for c in self._characters if c.pid in ALLIED_PIDS]

    @property
    def laguz_characters(self) -> list[CharacterEntry]:
        """Return characters with non-zero laguz gauge values (i.e., actual laguz)."""
        return [c for c in self._characters if c.is_laguz]

    @property
    def beorc_characters(self) -> list[CharacterEntry]:
        """Return characters that are NOT laguz."""
        return [c for c in self._characters if not c.is_laguz]

    def get(self, pid: str) -> CharacterEntry | None:
        return self._by_pid.get(pid)
