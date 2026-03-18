"""Shop data model with unified-with-overrides editing pattern.

Difficulty override resolution:
1. Start with vanilla inventory
2. Unified edit completely replaces vanilla for that chapter
3. Difficulty override replaces unified per shop type independently
"""


class ShopDatabase:
    def __init__(self, vanilla_weapons: dict[str, list[str]], vanilla_items: dict[str, list[str]]):
        self._vanilla_weapons = vanilla_weapons
        self._vanilla_items = vanilla_items
        self._unified: dict[str, dict] = {}
        self._overrides: dict[str, dict[str, dict]] = {}

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
        weapons = list(self._vanilla_weapons.get(chapter, []))
        items = list(self._vanilla_items.get(chapter, []))

        if chapter in self._unified:
            uni = self._unified[chapter]
            if "weapons" in uni:
                weapons = list(uni["weapons"])
            if "items" in uni:
                items = list(uni["items"])

        if difficulty in self._overrides and chapter in self._overrides[difficulty]:
            ovr = self._overrides[difficulty][chapter]
            if "weapons" in ovr:
                weapons = list(ovr["weapons"])
            if "items" in ovr:
                items = list(ovr["items"])

        return {"weapons": weapons, "items": items}

    def to_dict(self) -> dict:
        result = {"unified": {}, "overrides": {}}
        for ch, data in self._unified.items():
            result["unified"][ch] = dict(data)
        for diff, chapters in self._overrides.items():
            result["overrides"][diff] = {}
            for ch, data in chapters.items():
                result["overrides"][diff][ch] = dict(data)
        return result

    def load_from_dict(self, d: dict):
        self._unified = {}
        self._overrides = {}
        for ch, data in d.get("unified", {}).items():
            self._unified[ch] = dict(data)
        for diff, chapters in d.get("overrides", {}).items():
            self._overrides[diff] = {}
            for ch, data in chapters.items():
                self._overrides[diff][ch] = dict(data)
