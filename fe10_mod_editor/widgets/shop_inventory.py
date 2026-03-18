"""Checkbox item list with quick actions for shop inventory editing."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QAbstractItemView,
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QColor

from fe10_mod_editor.models.item_data import ItemEntry

UNSTOCKED_FG = QColor(160, 160, 160)


class ShopInventoryWidget(QWidget):
    """A checkbox item list for a single shop type (weapons or items).

    Displays all eligible items with checkboxes. Checked items are
    currently stocked; unchecked items are available to add and shown
    grayed out.

    Signals:
        inventory_changed(list[str]): Emitted with the current list of
            checked IIDs whenever the stocking changes.
    """

    inventory_changed = Signal(list)

    def __init__(self, title: str = "Shop", parent=None):
        super().__init__(parent)
        self._all_items: list[ItemEntry] = []
        self._stocked_set: set[str] = set()
        self._updating = False  # guard against recursive signals

        self._build_ui(title)

    def _build_ui(self, title: str):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(4, 4, 4, 4)

        # Title row
        title_row = QHBoxLayout()
        self._title_label = QLabel(f"<b>{title}</b>")
        title_row.addWidget(self._title_label)
        title_row.addStretch()
        self._counter_label = QLabel("0 / 0 items stocked")
        title_row.addWidget(self._counter_label)
        layout.addLayout(title_row)

        # Table
        self._table = QTableWidget()
        self._table.setColumnCount(4)
        self._table.setHorizontalHeaderLabels(["", "Name", "Type", "Price"])
        self._table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self._table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self._table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self._table.verticalHeader().setVisible(False)
        self._table.setSelectionMode(QAbstractItemView.NoSelection)
        self._table.setAlternatingRowColors(True)
        self._table.itemChanged.connect(self._on_item_changed)
        layout.addWidget(self._table)

        # Button row
        btn_row = QHBoxLayout()
        self._stock_all_btn = QPushButton("Stock All")
        self._stock_all_btn.clicked.connect(self._on_stock_all)
        btn_row.addWidget(self._stock_all_btn)

        self._clear_btn = QPushButton("Clear")
        self._clear_btn.clicked.connect(self._on_clear)
        btn_row.addWidget(self._clear_btn)

        btn_row.addStretch()
        layout.addLayout(btn_row)

    def set_items(self, all_items: list[ItemEntry], stocked_iids: list[str]):
        """Populate the table with all eligible items and check stocked ones."""
        self._updating = True
        self._all_items = list(all_items)
        self._stocked_set = set(stocked_iids)

        self._table.setRowCount(len(all_items))
        for row, item in enumerate(all_items):
            is_stocked = item.iid in self._stocked_set

            # Column 0: checkbox
            chk = QTableWidgetItem()
            chk.setFlags(Qt.ItemIsUserCheckable | Qt.ItemIsEnabled)
            chk.setCheckState(Qt.Checked if is_stocked else Qt.Unchecked)
            chk.setData(Qt.UserRole, item.iid)
            self._table.setItem(row, 0, chk)

            # Column 1: Name
            name_item = QTableWidgetItem(item.display_name)
            name_item.setFlags(Qt.ItemIsEnabled)
            if not is_stocked:
                name_item.setForeground(UNSTOCKED_FG)
            self._table.setItem(row, 1, name_item)

            # Column 2: Type
            type_item = QTableWidgetItem(item.weapon_type)
            type_item.setFlags(Qt.ItemIsEnabled)
            if not is_stocked:
                type_item.setForeground(UNSTOCKED_FG)
            self._table.setItem(row, 2, type_item)

            # Column 3: Price
            price_item = QTableWidgetItem(str(item.price))
            price_item.setFlags(Qt.ItemIsEnabled)
            price_item.setTextAlignment(int(Qt.AlignRight | Qt.AlignVCenter))
            if not is_stocked:
                price_item.setForeground(UNSTOCKED_FG)
            self._table.setItem(row, 3, price_item)

        self._update_counter()
        self._updating = False

    def get_stocked_iids(self) -> list[str]:
        """Return the list of currently checked item IIDs."""
        result = []
        for row in range(self._table.rowCount()):
            chk = self._table.item(row, 0)
            if chk is not None and chk.checkState() == Qt.Checked:
                iid = chk.data(Qt.UserRole)
                if iid:
                    result.append(iid)
        return result

    def _on_item_changed(self, item: QTableWidgetItem):
        """Handle checkbox state changes."""
        if self._updating:
            return
        if item.column() != 0:
            return

        row = item.row()
        is_checked = item.checkState() == Qt.Checked
        iid = item.data(Qt.UserRole)

        # Update the stocked set
        if is_checked:
            self._stocked_set.add(iid)
        else:
            self._stocked_set.discard(iid)

        # Update visual state of this row
        self._updating = True
        for col in range(1, 4):
            cell = self._table.item(row, col)
            if cell is not None:
                cell.setForeground(
                    QColor(0, 0, 0) if is_checked else UNSTOCKED_FG
                )
        self._updating = False

        self._update_counter()
        self.inventory_changed.emit(self.get_stocked_iids())

    def _on_stock_all(self):
        """Check all items."""
        self._updating = True
        for row in range(self._table.rowCount()):
            chk = self._table.item(row, 0)
            if chk is not None:
                chk.setCheckState(Qt.Checked)
                iid = chk.data(Qt.UserRole)
                if iid:
                    self._stocked_set.add(iid)
            for col in range(1, 4):
                cell = self._table.item(row, col)
                if cell is not None:
                    cell.setForeground(QColor(0, 0, 0))
        self._update_counter()
        self._updating = False
        self.inventory_changed.emit(self.get_stocked_iids())

    def _on_clear(self):
        """Uncheck all items."""
        self._updating = True
        for row in range(self._table.rowCount()):
            chk = self._table.item(row, 0)
            if chk is not None:
                chk.setCheckState(Qt.Unchecked)
            for col in range(1, 4):
                cell = self._table.item(row, col)
                if cell is not None:
                    cell.setForeground(UNSTOCKED_FG)
        self._stocked_set.clear()
        self._update_counter()
        self._updating = False
        self.inventory_changed.emit(self.get_stocked_iids())

    def _update_counter(self):
        """Update the counter label."""
        total = self._table.rowCount()
        stocked = sum(
            1 for row in range(total)
            if self._table.item(row, 0) is not None
            and self._table.item(row, 0).checkState() == Qt.Checked
        )
        self._counter_label.setText(f"{stocked} / {total} items stocked")
