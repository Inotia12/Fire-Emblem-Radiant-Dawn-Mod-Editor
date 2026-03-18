"""Info sub-tab editor for character metadata, class info, max stats, and laguz data."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QGridLayout, QLabel, QSpinBox, QComboBox,
    QGroupBox, QFrame,
)
from PySide6.QtCore import Qt, Signal

from fe10_mod_editor.models.character_data import CharacterEntry
from fe10_mod_editor.models.class_data import ClassEntry

# The 8 class max stats
_MAX_STAT_KEYS = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]

_STAT_LABELS = {
    "hp": "HP", "str": "Str", "mag": "Mag", "skl": "Skl",
    "spd": "Spd", "lck": "Lck", "def": "Def", "res": "Res",
}

# Biorhythm options: display text -> stored value
_BIORHYTHM_OPTIONS = [
    ("Best", 0),
    ("Good", 1),
    ("Average", 2),
    ("Bad", 3),
    ("Worst", 4),
    ("Type 5", 5),
    ("Type 6", 6),
    ("Type 7", 7),
    ("Type 8", 8),
    ("Type 9", 9),
    ("None", 255),
]

# Laguz gauge keys
_LAGUZ_GAUGE_KEYS = ["gain_turn", "gain_battle", "loss_turn", "loss_battle"]
_LAGUZ_GAUGE_LABELS = {
    "gain_turn": "Gauge Gain/Turn",
    "gain_battle": "Gauge Gain/Battle",
    "loss_turn": "Gauge Loss/Turn",
    "loss_battle": "Gauge Loss/Battle",
}


class CharacterInfoEditor(QWidget):
    """Editor panel for character info, class info, max stats, biorhythm, and laguz data.

    Emits field_changed(pid, field_path, value) for biorhythm and laguz gauge edits.
    Emits class_max_stats_changed(jid, stat_name, value) for class max stat edits.
    """

    field_changed = Signal(str, str, object)  # (pid, field_path, value)
    class_max_stats_changed = Signal(str, str, object)  # (jid, stat_name, value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_char: CharacterEntry | None = None
        self._current_class: ClassEntry | None = None
        self._loading = False
        self._max_stats_override_active = False

        self._max_stat_spins: dict[str, QSpinBox] = {}
        self._laguz_spins: dict[str, QSpinBox] = {}

        self._build_ui()
        self.setEnabled(False)

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---- Character Info (read-only) ----
        char_group = QGroupBox("Character Info")
        char_grid = QGridLayout(char_group)

        char_grid.addWidget(QLabel("PID"), 0, 0)
        self._pid_label = QLabel("-")
        self._pid_label.setStyleSheet("color: gray; font-size: 11px;")
        self._pid_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        char_grid.addWidget(self._pid_label, 0, 1)

        char_grid.addWidget(QLabel("Gender"), 1, 0)
        self._gender_label = QLabel("-")
        char_grid.addWidget(self._gender_label, 1, 1)

        layout.addWidget(char_group)

        # ---- Class Info (read-only) ----
        class_group = QGroupBox("Class Info")
        class_grid = QGridLayout(class_group)

        class_grid.addWidget(QLabel("Class"), 0, 0)
        self._class_name_label = QLabel("-")
        class_grid.addWidget(self._class_name_label, 0, 1)

        class_grid.addWidget(QLabel("Movement"), 1, 0)
        self._movement_label = QLabel("-")
        class_grid.addWidget(self._movement_label, 1, 1)

        class_grid.addWidget(QLabel("Skill Capacity"), 2, 0)
        self._skill_cap_label = QLabel("-")
        class_grid.addWidget(self._skill_cap_label, 2, 1)

        class_grid.addWidget(QLabel("Weapon Ranks"), 3, 0)
        self._weapon_ranks_label = QLabel("-")
        self._weapon_ranks_label.setWordWrap(True)
        class_grid.addWidget(self._weapon_ranks_label, 3, 1)

        layout.addWidget(class_group)

        # ---- Max Stats (editable, class-level) ----
        self._max_stats_group = QGroupBox("Max Stats (Class)")
        max_grid = QGridLayout(self._max_stats_group)

        self._max_stats_warning = QLabel("")
        self._max_stats_warning.setStyleSheet("color: #cc6600; font-size: 11px;")
        self._max_stats_warning.setWordWrap(True)
        max_grid.addWidget(self._max_stats_warning, 0, 0, 1, 2)

        for i, stat_key in enumerate(_MAX_STAT_KEYS):
            row = i + 1
            label_text = _STAT_LABELS.get(stat_key, stat_key.upper())

            max_grid.addWidget(QLabel(label_text), row, 0)
            spin = QSpinBox()
            spin.setRange(0, 255)
            spin.setMinimumWidth(70)
            self._max_stat_spins[stat_key] = spin
            spin.valueChanged.connect(
                lambda val, sk=stat_key: self._on_max_stat_changed(sk, val)
            )
            max_grid.addWidget(spin, row, 1)

        layout.addWidget(self._max_stats_group)

        # ---- Biorhythm ----
        bio_group = QGroupBox("Biorhythm")
        bio_grid = QGridLayout(bio_group)

        bio_grid.addWidget(QLabel("Type"), 0, 0)
        self._biorhythm_combo = QComboBox()
        for display_text, _value in _BIORHYTHM_OPTIONS:
            self._biorhythm_combo.addItem(display_text, userData=_value)
        self._biorhythm_combo.currentIndexChanged.connect(self._on_biorhythm_changed)
        bio_grid.addWidget(self._biorhythm_combo, 0, 1)

        layout.addWidget(bio_group)

        # ---- Laguz Data (conditionally visible) ----
        self._laguz_group = QGroupBox("Laguz Gauge")
        laguz_grid = QGridLayout(self._laguz_group)

        for i, key in enumerate(_LAGUZ_GAUGE_KEYS):
            label_text = _LAGUZ_GAUGE_LABELS[key]
            laguz_grid.addWidget(QLabel(label_text), i, 0)

            spin = QSpinBox()
            spin.setRange(-128, 127)
            spin.setMinimumWidth(70)
            self._laguz_spins[key] = spin
            spin.valueChanged.connect(
                lambda val, k=key: self._on_laguz_gauge_changed(k, val)
            )
            laguz_grid.addWidget(spin, i, 1)

        self._laguz_group.hide()
        layout.addWidget(self._laguz_group)

        layout.addStretch()

    def set_max_stats_override_active(self, active: bool):
        """Disable/enable max stat spinboxes based on the global set_all_max_stats toggle.

        When the misc set_all_max_stats is active, individual max stat edits are
        meaningless, so we disable the spinboxes.
        """
        self._max_stats_override_active = active
        for spin in self._max_stat_spins.values():
            spin.setEnabled(not active)
        if active:
            self._max_stats_warning.setText(
                "Disabled: global 'Set All Max Stats' is active in Misc settings."
            )
        else:
            self._update_max_stats_warning()

    def load_character(self, char: CharacterEntry, class_entry: ClassEntry | None,
                       edits: dict, class_edits: dict, misc: dict):
        """Populate the editor with character and class info.

        Args:
            char: The CharacterEntry to display.
            class_entry: The character's ClassEntry.
            edits: The character_edits dict for this PID (may be empty).
            class_edits: The class_max_stat_edits dict for this character's JID (may be empty).
            misc: The project misc dict (for checking set_all_max_stats).
        """
        self._loading = True
        self._current_char = char
        self._current_class = class_entry
        self.setEnabled(True)

        # ---- Character Info ----
        self._pid_label.setText(char.pid)
        gender_text = {0: "Male", 1: "Female"}.get(char.gender, f"Unknown ({char.gender})")
        self._gender_label.setText(gender_text)

        # ---- Class Info ----
        if class_entry:
            self._class_name_label.setText(class_entry.display_name)
            self._movement_label.setText(str(class_entry.default_movement))
            self._skill_cap_label.setText(str(class_entry.skill_capacity))
            self._weapon_ranks_label.setText(class_entry.weapon_ranks or "-")
        else:
            self._class_name_label.setText(char.jid)
            self._movement_label.setText("-")
            self._skill_cap_label.setText("-")
            self._weapon_ranks_label.setText("-")

        # ---- Max Stats ----
        class_changes = misc.get("class_changes", {})
        override_active = class_changes.get("set_all_max_stats", False)
        self.set_max_stats_override_active(override_active)

        for stat_key in _MAX_STAT_KEYS:
            # Prefer class_edits, then original class max stats
            if stat_key in class_edits:
                val = class_edits[stat_key]
            elif class_entry:
                val = class_entry.max_stats.get(stat_key, 0)
            else:
                val = 0
            self._max_stat_spins[stat_key].setValue(val)

        self._update_max_stats_warning()

        # ---- Biorhythm ----
        bio_value = edits.get("biorhythm_type", char.biorhythm_type)
        bio_idx = self._find_biorhythm_index(bio_value)
        self._biorhythm_combo.setCurrentIndex(bio_idx)

        # ---- Laguz Data ----
        if char.is_laguz:
            self._laguz_group.show()
            edit_laguz = edits.get("laguz_gauge", {})
            for key in _LAGUZ_GAUGE_KEYS:
                if key in edit_laguz:
                    val = edit_laguz[key]
                else:
                    val = char.laguz_gauge.get(key, 0)
                self._laguz_spins[key].setValue(val)
        else:
            self._laguz_group.hide()

        self._loading = False

    def _find_biorhythm_index(self, value: int) -> int:
        """Find the combo box index for a biorhythm value."""
        for i, (_text, val) in enumerate(_BIORHYTHM_OPTIONS):
            if val == value:
                return i
        # Default to Average (index 2) if unknown
        return 2

    def _update_max_stats_warning(self):
        """Update the max stats warning label."""
        if self._max_stats_override_active:
            return  # Already showing override message
        if self._current_class:
            self._max_stats_warning.setText(
                f"Warning: Affects ALL {self._current_class.display_name} characters."
            )
        else:
            self._max_stats_warning.setText("")

    def _on_max_stat_changed(self, stat_key: str, value: int):
        """Handle a max stat spin box change."""
        if self._loading or self._current_char is None:
            return
        jid = self._current_char.jid
        self.class_max_stats_changed.emit(jid, stat_key, value)

    def _on_biorhythm_changed(self, index: int):
        """Handle biorhythm combo box change."""
        if self._loading or self._current_char is None:
            return
        value = self._biorhythm_combo.currentData()
        if value is not None:
            self.field_changed.emit(
                self._current_char.pid,
                "biorhythm_type",
                value,
            )

    def _on_laguz_gauge_changed(self, key: str, value: int):
        """Handle laguz gauge spin box change."""
        if self._loading or self._current_char is None:
            return
        self.field_changed.emit(
            self._current_char.pid,
            f"laguz_gauge.{key}",
            value,
        )
