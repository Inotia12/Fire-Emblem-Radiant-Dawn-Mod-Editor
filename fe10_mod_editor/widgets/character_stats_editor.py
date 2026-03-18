"""Stats sub-tab editor for individual character stat adjustments and computed finals."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QGroupBox,
)
from PySide6.QtCore import Signal

from fe10_mod_editor.models.character_data import CharacterEntry
from fe10_mod_editor.models.class_data import ClassEntry

# The 10 stat adjustment keys in order (matches binary layout)
_ADJUSTMENT_STATS = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res", "con", "mov"]

# The 8 stats that have class bases (hp through res)
_BASE_STATS = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]

# Display labels for each stat
_STAT_LABELS = {
    "hp": "HP", "str": "Str", "mag": "Mag", "skl": "Skl",
    "spd": "Spd", "lck": "Lck", "def": "Def", "res": "Res",
    "con": "Con", "mov": "Mov",
}

WARNING_STYLE = "color: #cc6600; font-weight: bold;"


class CharacterStatsEditor(QWidget):
    """Editor panel for a character's stat adjustments with computed final values.

    Emits field_changed(pid, field_path, value) when a stat adjustment, level,
    or authority stars value is modified.
    """

    field_changed = Signal(str, str, object)  # (pid, field_path, value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_char: CharacterEntry | None = None
        self._current_class: ClassEntry | None = None
        self._loading = False

        self._adjustment_spins: dict[str, QSpinBox] = {}
        self._final_labels: dict[str, QLabel] = {}
        self._class_base_labels: dict[str, QLabel] = {}

        self._build_ui()
        self.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---- Stats Grid ----
        stats_group = QGroupBox("Stats (Class Base + Adjustment = Final)")
        stats_grid = QGridLayout(stats_group)

        # Header row
        stats_grid.addWidget(QLabel("Stat"), 0, 0)
        stats_grid.addWidget(QLabel("Final"), 0, 1)
        stats_grid.addWidget(QLabel("Adjustment"), 0, 2)
        stats_grid.addWidget(QLabel("Class Base"), 0, 3)

        for i, stat_key in enumerate(_ADJUSTMENT_STATS):
            row = i + 1
            label_text = _STAT_LABELS.get(stat_key, stat_key.upper())

            # Stat name
            stats_grid.addWidget(QLabel(label_text), row, 0)

            # Final (read-only)
            final_lbl = QLabel("0")
            final_lbl.setMinimumWidth(40)
            self._final_labels[stat_key] = final_lbl
            stats_grid.addWidget(final_lbl, row, 1)

            # Adjustment (editable)
            spin = QSpinBox()
            spin.setRange(-128, 127)
            spin.setMinimumWidth(70)
            self._adjustment_spins[stat_key] = spin
            spin.valueChanged.connect(
                lambda val, sk=stat_key: self._on_adjustment_changed(sk, val)
            )
            stats_grid.addWidget(spin, row, 2)

            # Class base (read-only)
            base_lbl = QLabel("0")
            base_lbl.setStyleSheet("color: gray;")
            self._class_base_labels[stat_key] = base_lbl
            stats_grid.addWidget(base_lbl, row, 3)

        layout.addWidget(stats_group)

        # ---- Level & Authority ----
        misc_group = QGroupBox("Level & Authority")
        misc_grid = QGridLayout(misc_group)

        misc_grid.addWidget(QLabel("Level"), 0, 0)
        self._level_spin = QSpinBox()
        self._level_spin.setRange(1, 40)
        self._level_spin.valueChanged.connect(self._on_level_changed)
        misc_grid.addWidget(self._level_spin, 0, 1)

        misc_grid.addWidget(QLabel("Authority Stars"), 1, 0)
        self._authority_spin = QSpinBox()
        self._authority_spin.setRange(0, 5)
        self._authority_spin.valueChanged.connect(self._on_authority_changed)
        misc_grid.addWidget(self._authority_spin, 1, 1)

        layout.addWidget(misc_group)

        layout.addStretch()

    def load_character(self, char: CharacterEntry, class_entry: ClassEntry | None,
                       edits: dict):
        """Populate the editor with a character's stat data.

        Args:
            char: The CharacterEntry to display.
            class_entry: The character's ClassEntry (for base stats and max stats).
            edits: The character_edits dict for this PID (may be empty).
        """
        self._loading = True
        self._current_char = char
        self._current_class = class_entry
        self.setEnabled(True)

        edit_adjustments = edits.get("stat_adjustments", {})

        for stat_key in _ADJUSTMENT_STATS:
            # Get class base (only hp-res have class bases; con/mov do not)
            class_base = 0
            if class_entry and stat_key in _BASE_STATS:
                class_base = class_entry.base_stats.get(stat_key, 0)

            # Get adjustment (prefer edits)
            if stat_key in edit_adjustments:
                adjustment = edit_adjustments[stat_key]
            else:
                adjustment = char.stat_adjustments.get(stat_key, 0)

            final = class_base + adjustment

            # Update UI
            self._class_base_labels[stat_key].setText(str(class_base))
            self._adjustment_spins[stat_key].setValue(adjustment)
            self._final_labels[stat_key].setText(str(final))

            # Highlight if final exceeds class max stat
            self._update_final_highlight(stat_key, final, class_entry)

        # Level
        level = edits.get("level", char.level)
        self._level_spin.setValue(level)

        # Authority stars
        authority = edits.get("authority_stars", char.authority_stars)
        self._authority_spin.setValue(authority)

        self._loading = False

    def _update_final_highlight(self, stat_key: str, final: int,
                                class_entry: ClassEntry | None):
        """Apply yellow warning style if the final exceeds the class max stat."""
        label = self._final_labels[stat_key]
        if class_entry and stat_key in _BASE_STATS:
            max_stat = class_entry.max_stats.get(stat_key, 255)
            if final > max_stat:
                label.setStyleSheet(WARNING_STYLE)
                label.setToolTip(f"Exceeds class max of {max_stat}")
                return
        label.setStyleSheet("")
        label.setToolTip("")

    def _recalculate_final(self, stat_key: str):
        """Recalculate and display the final stat value for a single stat."""
        class_base = 0
        if self._current_class and stat_key in _BASE_STATS:
            class_base = self._current_class.base_stats.get(stat_key, 0)

        adjustment = self._adjustment_spins[stat_key].value()
        final = class_base + adjustment

        self._final_labels[stat_key].setText(str(final))
        self._update_final_highlight(stat_key, final, self._current_class)

    def _on_adjustment_changed(self, stat_key: str, value: int):
        """Handle an adjustment spin box change."""
        if self._loading or self._current_char is None:
            return
        self._recalculate_final(stat_key)
        self.field_changed.emit(
            self._current_char.pid,
            f"stat_adjustments.{stat_key}",
            value,
        )

    def _on_level_changed(self, value: int):
        """Handle level spin box change."""
        if self._loading or self._current_char is None:
            return
        self.field_changed.emit(self._current_char.pid, "level", value)

    def _on_authority_changed(self, value: int):
        """Handle authority stars spin box change."""
        if self._loading or self._current_char is None:
            return
        self.field_changed.emit(self._current_char.pid, "authority_stars", value)
