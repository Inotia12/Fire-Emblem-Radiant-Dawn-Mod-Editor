"""Skill data model — wraps parsed skill data with display logic and restriction checks."""

from dataclasses import dataclass, field


def display_name_from_sid(sid: str) -> str:
    """Convert SID to display name: strip 'SID_', replace '_' with ' ', title case."""
    name = sid
    if name.startswith("SID_"):
        name = name[4:]
    return name.replace("_", " ").title()


@dataclass
class SkillEntry:
    sid: str
    msid: str
    capacity_cost: int
    visibility: int  # 1=visible, 2=grayed, 3=hidden
    whitelist: list = field(default_factory=list)  # Restriction table 1: allowed JIDs/SIDs
    blacklist: list = field(default_factory=list)  # Restriction table 2: forbidden JIDs/SIDs
    byte_offset: int = 0

    @property
    def display_name(self) -> str:
        return display_name_from_sid(self.sid)

    @property
    def is_visible(self) -> bool:
        return self.visibility == 1


class SkillDatabase:
    def __init__(self, skills: list[SkillEntry]):
        self._skills = skills
        self._by_sid = {s.sid: s for s in skills}

    @classmethod
    def from_parsed(cls, parsed: list[dict]) -> "SkillDatabase":
        """Build a SkillDatabase from a list of dicts returned by parse_all_skills."""
        entries = [
            SkillEntry(
                sid=p["sid"],
                msid=p.get("msid", ""),
                capacity_cost=p.get("capacity_cost", 0),
                visibility=p.get("visibility", 1),
                whitelist=p.get("whitelist", []),
                blacklist=p.get("blacklist", []),
                byte_offset=p.get("byte_offset", 0),
            )
            for p in parsed
        ]
        return cls(entries)

    @property
    def count(self) -> int:
        return len(self._skills)

    @property
    def all_skills(self) -> list[SkillEntry]:
        return list(self._skills)

    def get(self, sid: str) -> SkillEntry | None:
        return self._by_sid.get(sid)

    def check_restriction(self, sid: str, jid: str) -> str | None:
        """Check whether a skill can be assigned to a class.

        Returns a human-readable reason string if the assignment is restricted,
        or None if the skill can be freely assigned to the class.

        Args:
            sid: Skill ID to check (e.g. "SID_HOWL").
            jid: Class ID to check against (e.g. "JID_BRAVE").

        Returns:
            str describing the restriction, or None if no restriction applies.
        """
        skill = self._by_sid.get(sid)
        if skill is None:
            return f"Unknown skill: {sid}"

        # If a whitelist exists, the skill is only allowed for those entries.
        if skill.whitelist and jid not in skill.whitelist:
            return f"{sid} is restricted to {skill.whitelist}"

        # If the jid is on the blacklist, the skill is forbidden for it.
        if jid in skill.blacklist:
            return f"{sid} is forbidden for {jid}"

        return None
