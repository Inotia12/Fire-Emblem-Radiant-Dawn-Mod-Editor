"""Project file (.fe10mod) management — load, save, validate."""

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
