"""Items tab — filterable item table with side-panel editor."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLineEdit, QPushButton, QTableView, QAbstractItemView, QHeaderView,
)
from PySide6.QtCore import Qt

from fe10_mod_editor.models.item_data import ItemDatabase
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.widgets.item_table import ItemTableModel, ItemSortFilterProxy
from fe10_mod_editor.widgets.item_editor import ItemEditor

# Weapon type filter buttons to show
FILTER_TYPES = [
    "sword", "lance", "axe", "bow", "knife",
    "flame", "thunder", "wind", "light", "dark",
]


class ItemsTab(QWidget):
    """Main Items tab with filter bar, sortable table, and editor side panel."""

    def __init__(self, project: ProjectFile,
                 item_database: ItemDatabase | None = None,
                 parent=None):
        super().__init__(parent)
        self.project = project
        self.item_database = item_database

        self._active_type_filter: str | None = None
        self._type_buttons: dict[str, QPushButton] = {}

        self._build_ui()
        self._connect_signals()

    def set_data_source(self, item_database: ItemDatabase | None,
                        project: ProjectFile):
        """Update the backing data and refresh all widgets."""
        self.item_database = item_database
        self.project = project
        self._model.set_data_source(item_database, project.item_edits)
        self._editor.set_item_edits(project.item_edits)
        self._editor.load_item(None)

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left side: filter bar + table ----
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)

        # Filter bar
        filter_bar = QHBoxLayout()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search items...")
        self._search_input.setClearButtonEnabled(True)
        filter_bar.addWidget(self._search_input, stretch=1)

        left_layout.addLayout(filter_bar)

        # Type filter buttons
        type_bar = QHBoxLayout()
        type_bar.setSpacing(2)

        all_btn = QPushButton("All")
        all_btn.setCheckable(True)
        all_btn.setChecked(True)
        all_btn.setMaximumWidth(50)
        all_btn.clicked.connect(lambda: self._on_type_filter(None))
        type_bar.addWidget(all_btn)
        self._type_buttons[None] = all_btn

        for wtype in FILTER_TYPES:
            btn = QPushButton(wtype.capitalize())
            btn.setCheckable(True)
            btn.setMaximumWidth(70)
            btn.clicked.connect(lambda checked, t=wtype: self._on_type_filter(t))
            type_bar.addWidget(btn)
            self._type_buttons[wtype] = btn

        type_bar.addStretch()
        left_layout.addLayout(type_bar)

        # Item table
        self._model = ItemTableModel(
            self.item_database, self.project.item_edits
        )
        self._proxy = ItemSortFilterProxy()
        self._proxy.setSourceModel(self._model)

        self._table = QTableView()
        self._table.setModel(self._proxy)
        self._table.setSortingEnabled(True)
        self._table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self._table.setSelectionMode(QAbstractItemView.SingleSelection)
        self._table.setAlternatingRowColors(True)
        self._table.verticalHeader().setVisible(False)
        self._table.horizontalHeader().setStretchLastSection(True)
        self._table.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents
        )

        left_layout.addWidget(self._table)

        # ---- Right side: editor ----
        self._editor = ItemEditor()
        self._editor.set_item_edits(self.project.item_edits)

        splitter.addWidget(left_widget)
        splitter.addWidget(self._editor)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 1)

        outer_layout.addWidget(splitter)

    def _connect_signals(self):
        # Search text -> proxy filter
        self._search_input.textChanged.connect(self._proxy.set_search_text)

        # Table selection -> editor
        self._table.selectionModel().currentRowChanged.connect(
            self._on_row_selected
        )

        # Editor changes -> project edits + table refresh
        self._editor.field_changed.connect(self._on_field_changed)

    def _on_type_filter(self, weapon_type: str | None):
        """Handle type filter button click."""
        self._active_type_filter = weapon_type
        self._proxy.set_type_filter(weapon_type)

        # Update button checked states
        for wtype, btn in self._type_buttons.items():
            btn.setChecked(wtype == weapon_type)

    def _on_row_selected(self, current, previous):
        """Handle table row selection change."""
        if not current.isValid():
            self._editor.load_item(None)
            return

        # Map proxy index to source index
        source_index = self._proxy.mapToSource(current)
        item = self._model.item_at_row(source_index.row())
        self._editor.load_item(item)

    def _on_field_changed(self, iid: str, field_name: str, value):
        """Handle a field change from the editor."""
        if field_name == "__reset__":
            # Item was reset — edits already cleared by editor
            self._model.refresh()
            return

        # Get original value from database
        if self.item_database is None:
            return
        item = self.item_database.get(iid)
        if item is None:
            return

        original = getattr(item, field_name, None)

        if value == original:
            # Value matches original — remove from edits if present
            if iid in self.project.item_edits:
                self.project.item_edits[iid].pop(field_name, None)
                if not self.project.item_edits[iid]:
                    del self.project.item_edits[iid]
        else:
            # Store the edit
            if iid not in self.project.item_edits:
                self.project.item_edits[iid] = {}
            self.project.item_edits[iid][field_name] = value

        self._model.refresh()
