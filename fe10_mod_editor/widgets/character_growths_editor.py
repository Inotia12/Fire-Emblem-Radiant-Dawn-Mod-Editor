"""Growths sub-tab editor for individual character growth rates."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QGroupBox,
)
from PySide6.QtCore import Signal

from fe10_mod_editor.models.character_data import CharacterEntry
from fe10_mod_editor.models.class_data import ClassEntry

# The 8 growth rate stats (matches binary layout)
_GROWTH_STATS = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]

# Display labels
_STAT_LABELS = {
    "hp": "HP", "str": "Str", "mag": "Mag", "skl": "Skl",
    "spd": "Spd", "lck": "Lck", "def": "Def", "res": "Res",
}

WARNING_STYLE = "color: #cc6600; font-weight: bold;"


class CharacterGrowthsEditor(QWidget):
    """Editor panel for a character's growth rates.

    Shows personal growth rates alongside class growth rates.
    Emits field_changed(pid, field_path, value) when a growth rate is modified.
    """

    field_changed = Signal(str, str, object)  # (pid, field_path, value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_char: CharacterEntry | None = None
        self._current_class: ClassEntry | None = None
        self._loading = False

        self._growth_spins: dict[str, QSpinBox] = {}
        self._class_growth_labels: dict[str, QLabel] = {}

        self._build_ui()
        self.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        growths_group = QGroupBox("Growth Rates (%)")
        growths_grid = QGridLayout(growths_group)

        # Header row
        growths_grid.addWidget(QLabel("Stat"), 0, 0)
        growths_grid.addWidget(QLabel("Personal"), 0, 1)
        growths_grid.addWidget(QLabel("Class Growth"), 0, 2)

        for i, stat_key in enumerate(_GROWTH_STATS):
            row = i + 1
            label_text = _STAT_LABELS.get(stat_key, stat_key.upper())

            # Stat name
            growths_grid.addWidget(QLabel(label_text), row, 0)

            # Personal growth (editable)
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setSuffix("%")
            spin.setMinimumWidth(80)
            self._growth_spins[stat_key] = spin
            spin.valueChanged.connect(
                lambda val, sk=stat_key: self._on_growth_changed(sk, val)
            )
            growths_grid.addWidget(spin, row, 1)

            # Class growth (read-only subtitle)
            class_lbl = QLabel("Class: +0%")
            class_lbl.setStyleSheet("color: gray; font-size: 11px;")
            self._class_growth_labels[stat_key] = class_lbl
            growths_grid.addWidget(class_lbl, row, 2)

        layout.addWidget(growths_group)
        layout.addStretch()

    def load_character(self, char: CharacterEntry, class_entry: ClassEntry | None,
                       edits: dict):
        """Populate the editor with a character's growth rate data.

        Args:
            char: The CharacterEntry to display.
            class_entry: The character's ClassEntry (for class growth rates).
            edits: The character_edits dict for this PID (may be empty).
        """
        self._loading = True
        self._current_char = char
        self._current_class = class_entry
        self.setEnabled(True)

        edit_growths = edits.get("growth_rates", {})

        for stat_key in _GROWTH_STATS:
            # Get personal growth (prefer edits)
            if stat_key in edit_growths:
                growth = edit_growths[stat_key]
            else:
                growth = char.growth_rates.get(stat_key, 0)

            # Get class growth
            class_growth = 0
            if class_entry:
                class_growth = class_entry.class_growth_rates.get(stat_key, 0)

            # Update UI
            self._growth_spins[stat_key].setValue(growth)
            self._class_growth_labels[stat_key].setText(f"Class: +{class_growth}%")
            self._class_growth_labels[stat_key].setToolTip(
                f"Class growth rate: {class_growth}%"
            )

            # Highlight if personal growth > 100%
            self._update_growth_highlight(stat_key, growth)

        self._loading = False

    def _update_growth_highlight(self, stat_key: str, growth: int):
        """Apply yellow warning if growth exceeds 100%."""
        spin = self._growth_spins[stat_key]
        if growth > 100:
            spin.setStyleSheet(WARNING_STYLE)
            spin.setToolTip(f"Growth rate exceeds 100% ({growth}%)")
        else:
            spin.setStyleSheet("")
            spin.setToolTip("")

    def _on_growth_changed(self, stat_key: str, value: int):
        """Handle a growth rate spin box change."""
        if self._loading or self._current_char is None:
            return
        self._update_growth_highlight(stat_key, value)
        self.field_changed.emit(
            self._current_char.pid,
            f"growth_rates.{stat_key}",
            value,
        )
