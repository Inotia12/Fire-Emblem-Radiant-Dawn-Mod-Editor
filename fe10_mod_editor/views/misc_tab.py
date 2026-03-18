"""Misc tab — batch toggle operations organized by category."""

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QScrollArea
from fe10_mod_editor.widgets.toggle_card import ToggleCard

WEAPON_CHANGES = [
    {
        "key": "remove_prf_locks",
        "title": "Remove PRF Locks",
        "description": "Changes weapon rank from N (personal) to D on all PRF weapons, "
                       "removes equip-lock attributes. Allows any character to equip "
                       "previously locked weapons like Ragnell, Alondite, etc.",
        "count": 18,
    },
    {
        "key": "remove_valuable",
        "title": "Remove Valuable Flag",
        "description": "Removes the 'valuable' attribute from all items. "
                       "Valuable items cannot be discarded or sold.",
        "count": 34,
    },
    {
        "key": "remove_seal_steal",
        "title": "Remove Steal Protection",
        "description": "Removes the 'sealsteal' attribute from all items. "
                       "Makes all items stealable.",
        "count": 9,
    },
]


class MiscTab(QWidget):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self._cards: dict[str, ToggleCard] = {}

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        layout = QVBoxLayout(content)

        # Weapon Changes category
        header = QLabel("<h2>Weapon Changes</h2>")
        layout.addWidget(header)

        for toggle_def in WEAPON_CHANGES:
            card = ToggleCard(
                key=toggle_def["key"],
                title=toggle_def["title"],
                description=toggle_def["description"],
                affected_count=toggle_def["count"],
            )
            card.toggled.connect(self._on_toggle)
            layout.addWidget(card)
            self._cards[toggle_def["key"]] = card

        layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        self._sync_from_project()

    def _sync_from_project(self):
        wc = self.project.misc.get("weapon_changes", {})
        for key, card in self._cards.items():
            card.set_checked(wc.get(key, False))

    def _on_toggle(self, key: str, checked: bool):
        self.project.misc.setdefault("weapon_changes", {})[key] = checked
