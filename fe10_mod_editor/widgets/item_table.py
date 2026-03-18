"""Filterable, sortable item table model and proxy for the Items tab."""

from PySide6.QtCore import (
    QAbstractTableModel, QModelIndex, QSortFilterProxyModel, Qt,
)
from PySide6.QtGui import QColor

from fe10_mod_editor.models.item_data import ItemDatabase, ItemEntry

COLUMNS = ["Name", "Type", "Rank", "Mt", "Hit", "Crt", "Wt", "Uses", "Price", "PRF"]

# Fields that map from column index to ItemEntry attribute name
_COL_FIELDS = [
    "display_name",  # 0 - Name
    "weapon_type",   # 1 - Type
    "weapon_rank",   # 2 - Rank
    "might",         # 3 - Mt
    "accuracy",      # 4 - Hit
    "critical",      # 5 - Crt
    "weight",        # 6 - Wt
    "uses",          # 7 - Uses
    "price",         # 8 - Price
    None,            # 9 - PRF (computed)
]

# Editable fields that can appear in item_edits (maps field name to column index)
EDITABLE_FIELDS = {
    "might": 3,
    "accuracy": 4,
    "critical": 5,
    "weight": 6,
    "uses": 7,
    "price": 8,
    "weapon_rank": 2,
    "wexp_gain": None,  # not in table but editable
}

MODIFIED_BG = QColor(255, 255, 200)  # light yellow


class ItemTableModel(QAbstractTableModel):
    """Table model backed by an ItemDatabase with an item_edits overlay."""

    def __init__(self, item_database: ItemDatabase | None = None,
                 item_edits: dict | None = None, parent=None):
        super().__init__(parent)
        self._db = item_database
        self._items: list[ItemEntry] = item_database.all_items if item_database else []
        self._edits: dict[str, dict] = item_edits if item_edits is not None else {}

    def set_data_source(self, item_database: ItemDatabase | None,
                        item_edits: dict | None):
        """Replace the backing data source and refresh."""
        self.beginResetModel()
        self._db = item_database
        self._items = item_database.all_items if item_database else []
        self._edits = item_edits if item_edits is not None else {}
        self.endResetModel()

    def refresh(self):
        """Signal full table refresh (e.g. after an edit)."""
        top_left = self.index(0, 0)
        bottom_right = self.index(self.rowCount() - 1, self.columnCount() - 1)
        if self.rowCount() > 0:
            self.dataChanged.emit(top_left, bottom_right)

    # ---- QAbstractTableModel interface ----

    def rowCount(self, parent=QModelIndex()):
        return len(self._items)

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
        if row < 0 or row >= len(self._items):
            return None

        item = self._items[row]
        edits = self._edits.get(item.iid, {})

        if role == Qt.DisplayRole:
            return self._display_value(item, edits, col)
        elif role == Qt.BackgroundRole:
            if item.iid in self._edits and self._edits[item.iid]:
                return MODIFIED_BG
            return None
        elif role == Qt.UserRole:
            # Return the IID for selection purposes
            return item.iid
        elif role == Qt.TextAlignmentRole:
            # Right-align numeric columns
            if col >= 3 and col <= 8:
                return int(Qt.AlignRight | Qt.AlignVCenter)
            return None

        return None

    def _display_value(self, item: ItemEntry, edits: dict, col: int):
        """Get the display value for a cell, preferring edits over originals."""
        if col == 0:  # Name
            return item.display_name
        elif col == 1:  # Type
            return item.weapon_type
        elif col == 2:  # Rank
            return edits.get("weapon_rank", item.weapon_rank)
        elif col == 3:  # Mt
            return edits.get("might", item.might)
        elif col == 4:  # Hit
            return edits.get("accuracy", item.accuracy)
        elif col == 5:  # Crt
            return edits.get("critical", item.critical)
        elif col == 6:  # Wt
            return edits.get("weight", item.weight)
        elif col == 7:  # Uses
            return edits.get("uses", item.uses)
        elif col == 8:  # Price
            return edits.get("price", item.price)
        elif col == 9:  # PRF
            return "PRF" if item.has_prf else ""
        return None

    def item_at_row(self, row: int) -> ItemEntry | None:
        """Return the ItemEntry at the given source model row."""
        if 0 <= row < len(self._items):
            return self._items[row]
        return None


class ItemSortFilterProxy(QSortFilterProxyModel):
    """Proxy that filters by weapon type and search text."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._type_filter: str | None = None
        self._search_text: str = ""
        self.setFilterCaseSensitivity(Qt.CaseInsensitive)
        self.setSortCaseSensitivity(Qt.CaseInsensitive)

    def set_type_filter(self, weapon_type: str | None):
        """Filter by weapon type (None = show all)."""
        self._type_filter = weapon_type
        self.invalidateFilter()

    def set_search_text(self, text: str):
        """Filter by item name/IID substring."""
        self._search_text = text.lower()
        self.invalidateFilter()

    def filterAcceptsRow(self, source_row, source_parent):
        model = self.sourceModel()
        if not isinstance(model, ItemTableModel):
            return True

        item = model.item_at_row(source_row)
        if item is None:
            return False

        # Type filter
        if self._type_filter is not None:
            if item.weapon_type != self._type_filter:
                return False

        # Search text filter
        if self._search_text:
            name_match = self._search_text in item.display_name.lower()
            iid_match = self._search_text in item.iid.lower()
            if not (name_match or iid_match):
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
