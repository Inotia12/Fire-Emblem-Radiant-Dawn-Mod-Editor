"""Filterable, sortable character table model and proxy for the Characters tab."""

from PySide6.QtCore import (
    QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt,
)
from PySide6.QtGui import QColor

from fe10_mod_editor.models.character_data import (
    CharacterDatabase, CharacterEntry, ALLIED_PIDS,
)
from fe10_mod_editor.models.class_data import ClassDatabase, ClassEntry

COLUMNS = ["Name", "Class", "Lv", "HP", "Str", "Mag", "Skl", "Spd", "Lck", "Def", "Res"]

# Stat keys that correspond to columns 3..10 (HP through Res)
_STAT_KEYS = ["hp", "str", "mag", "skl", "spd", "lck", "def", "res"]

MODIFIED_BG = QColor(255, 255, 200)  # light yellow


class CharacterTableModel(QAbstractTableModel):
    """Table model backed by CharacterDatabase + ClassDatabase with a character_edits overlay.

    Stats shown are COMPUTED finals: class base_stat + character stat_adjustment.
    If the character has edits, those override the original adjustments.
    """

    def __init__(self, char_db: CharacterDatabase | None = None,
                 class_db: ClassDatabase | None = None,
                 character_edits: dict | None = None, parent=None):
        super().__init__(parent)
        self._char_db = char_db
        self._class_db = class_db
        self._characters: list[CharacterEntry] = char_db.all_characters if char_db else []
        self._edits: dict[str, dict] = character_edits if character_edits is not None else {}

    def set_data_source(self, char_db: CharacterDatabase | None,
                        class_db: ClassDatabase | None,
                        character_edits: dict | None):
        """Replace the backing data source and refresh."""
        self.beginResetModel()
        self._char_db = char_db
        self._class_db = class_db
        self._characters = char_db.all_characters if char_db else []
        self._edits = character_edits if character_edits is not None else {}
        self.endResetModel()

    def refresh(self):
        """Signal full table refresh (e.g. after an edit)."""
        top_left = self.index(0, 0)
        bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
        if self.rowCount() > 0:
            self.dataChanged.emit(top_left, bottom_right)

    # ---- QAbstractTableModel interface ----

    def rowCount(self, parent=QModelIndex()):
        return len(self._characters)

    def columnCount(self, parent=QModelIndex()):
        return len(COLUMNS)

    def headerData(self, section, orientation, role=Qt.DisplayRole):
        if role == Qt.DisplayRole and orientation == Qt.Horizontal:
            return COLUMNS[section]
        return None

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid():
            return None
        row, col = index.row(), index.column()
        if row < 0 or row >= len(self._characters):
            return None

        char = self._characters[row]
        edits = self._edits.get(char.pid, {})

        if role == Qt.DisplayRole:
            return self._display_value(char, edits, col)
        elif role == Qt.BackgroundRole:
            if char.pid in self._edits and self._edits[char.pid]:
                return MODIFIED_BG
            return None
        elif role == Qt.UserRole:
            # Return the CharacterEntry for selection / filtering purposes
            return char
        elif role == Qt.TextAlignmentRole:
            # Right-align numeric columns (Lv and stats)
            if col >= 2:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return None

        return None

    def _display_value(self, char: CharacterEntry, edits: dict, col: int):
        """Get the display value for a cell, computing final stats from class + adjustments."""
        if col == 0:  # Name
            return char.display_name
        elif col == 1:  # Class
            class_entry = self._class_db.get(char.jid) if self._class_db else None
            return class_entry.display_name if class_entry else char.jid
        elif col == 2:  # Lv
            return edits.get("level", char.level)

        # Columns 3-10: computed final stats (class base + adjustment)
        stat_idx = col - 3
        if 0 <= stat_idx < len(_STAT_KEYS):
            stat_key = _STAT_KEYS[stat_idx]
            return self._compute_final_stat(char, edits, stat_key)

        return None

    def _compute_final_stat(self, char: CharacterEntry, edits: dict, stat_key: str) -> int:
        """Compute final stat = class base + character adjustment (with edit overlay)."""
        # Get class base stat
        class_base = 0
        if self._class_db:
            class_entry = self._class_db.get(char.jid)
            if class_entry:
                class_base = class_entry.base_stats.get(stat_key, 0)

        # Get adjustment (prefer edit overlay)
        edit_adjustments = edits.get("stat_adjustments", {})
        if stat_key in edit_adjustments:
            adjustment = edit_adjustments[stat_key]
        else:
            adjustment = char.stat_adjustments.get(stat_key, 0)

        return class_base + adjustment

    def character_at_row(self, row: int) -> CharacterEntry | None:
        """Return the CharacterEntry at the given source model row."""
        if 0 <= row < len(self._characters):
            return self._characters[row]
        return None


class CharacterSortFilterProxy(QSortFilterProxyModel):
    """Proxy that filters by character type (allied/laguz/beorc/all) and search text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._filter_type: str = "all"
        self._search_text: str = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def set_filter_type(self, filter_type: str):
        """Filter by character type: 'allied', 'laguz', 'beorc', or 'all'."""
        self._filter_type = filter_type
        self.invalidateFilter()

    def set_search_text(self, text: str):
        """Filter by character name/PID substring."""
        self._search_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if not isinstance(model, CharacterTableModel):
            return True

        char = model.character_at_row(source_row)
        if char is None:
            return False

        # Type filter
        if self._filter_type == "allied":
            if char.pid not in ALLIED_PIDS:
                return False
        elif self._filter_type == "laguz":
            if not char.is_laguz:
                return False
        elif self._filter_type == "beorc":
            if char.is_laguz:
                return False
        # "all" shows everything

        # Search text filter
        if self._search_text:
            name_match = self._search_text in char.display_name.lower()
            pid_match = self._search_text in char.pid.lower()
            if not (name_match or pid_match):
                return False

        return True

    def lessThan(self, left, right):
        """Custom sorting: numeric columns sort numerically."""
        left_data = self.sourceModel().data(left, Qt.DisplayRole)
        right_data = self.sourceModel().data(right, Qt.DisplayRole)

        # Try numeric comparison
        if isinstance(left_data, (int, float)) and isinstance(right_data, (int, float)):
            return left_data < right_data

        # Fall back to string comparison
        return str(left_data or "") < str(right_data or "")
