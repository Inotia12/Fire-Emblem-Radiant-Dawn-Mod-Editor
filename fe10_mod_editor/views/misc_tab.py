"""Misc tab — batch toggle operations organized by category."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QScrollArea, QComboBox, QSpinBox,
)
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

CLASS_CHANGES = [
    {
        "key": "set_all_max_stats",
        "title": "Set All Max Stats",
        "description": "Sets every class's max stat caps to the selected value "
                       "(+20 for HP). Individual max stat edits are preserved "
                       "but suppressed while this is active.",
        "count": 171,
    },
]

# Preset values for the max stats selector
_MAX_STATS_PRESETS = [40, 60, 80]


class MiscTab(QWidget):
    def __init__(self, project, parent=None):
        super().__init__(parent)
        self.project = project
        self._cards: dict[str, ToggleCard] = {}
        self._loading = False

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

        # Class Changes category
        class_header = QLabel("<h2>Class Changes</h2>")
        layout.addWidget(class_header)

        for toggle_def in CLASS_CHANGES:
            card = ToggleCard(
                key=toggle_def["key"],
                title=toggle_def["title"],
                description=toggle_def["description"],
                affected_count=toggle_def["count"],
            )
            card.toggled.connect(self._on_class_toggle)
            layout.addWidget(card)
            self._cards[toggle_def["key"]] = card

        # Max stats preset selector (below the toggle card)
        preset_row = QHBoxLayout()
        preset_row.setContentsMargins(16, 0, 16, 0)
        preset_label = QLabel("Max stats value:")
        preset_label.setStyleSheet("font-weight: bold;")
        preset_row.addWidget(preset_label)

        self._preset_combo = QComboBox()
        for val in _MAX_STATS_PRESETS:
            self._preset_combo.addItem(str(val), userData=val)
        self._preset_combo.addItem("Custom", userData="custom")
        self._preset_combo.setMinimumWidth(80)
        self._preset_combo.currentIndexChanged.connect(self._on_preset_changed)
        preset_row.addWidget(self._preset_combo)

        self._custom_spin = QSpinBox()
        self._custom_spin.setRange(1, 255)
        self._custom_spin.setMinimumWidth(70)
        self._custom_spin.hide()
        self._custom_spin.valueChanged.connect(self._on_custom_value_changed)
        preset_row.addWidget(self._custom_spin)

        preset_row.addStretch()
        layout.addLayout(preset_row)

        layout.addStretch()
        scroll.setWidget(content)

        outer = QVBoxLayout(self)
        outer.addWidget(scroll)

        self._sync_from_project()

    def _sync_from_project(self):
        self._loading = True

        # Weapon changes
        wc = self.project.misc.get("weapon_changes", {})
        for key in ("remove_prf_locks", "remove_valuable", "remove_seal_steal"):
            if key in self._cards:
                self._cards[key].set_checked(wc.get(key, False))

        # Class changes
        cc = self.project.misc.get("class_changes", {})
        if "set_all_max_stats" in self._cards:
            self._cards["set_all_max_stats"].set_checked(cc.get("set_all_max_stats", False))

        # Max stats preset
        preset_value = cc.get("max_stats_preset", 40)
        if preset_value in _MAX_STATS_PRESETS:
            idx = _MAX_STATS_PRESETS.index(preset_value)
            self._preset_combo.setCurrentIndex(idx)
            self._custom_spin.hide()
        else:
            # Custom value
            self._preset_combo.setCurrentIndex(len(_MAX_STATS_PRESETS))  # "Custom" index
            self._custom_spin.setValue(preset_value)
            self._custom_spin.show()

        self._loading = False

    def _on_toggle(self, key: str, checked: bool):
        self.project.misc.setdefault("weapon_changes", {})[key] = checked

    def _on_class_toggle(self, key: str, checked: bool):
        self.project.misc.setdefault("class_changes", {})[key] = checked

    def _on_preset_changed(self, index: int):
        if self._loading:
            return
        data = self._preset_combo.currentData()
        if data == "custom":
            self._custom_spin.show()
            value = self._custom_spin.value()
        else:
            self._custom_spin.hide()
            value = data
        self.project.misc.setdefault("class_changes", {})["max_stats_preset"] = value

    def _on_custom_value_changed(self, value: int):
        if self._loading:
            return
        self.project.misc.setdefault("class_changes", {})["max_stats_preset"] = value
