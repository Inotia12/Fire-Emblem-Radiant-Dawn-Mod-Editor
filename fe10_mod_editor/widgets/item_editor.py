"""Side panel editor widget for editing individual item properties."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout,
    QLabel, QSpinBox, QComboBox, QPushButton, QGroupBox, QFrame,
)
from PySide6.QtCore import Signal

from fe10_mod_editor.models.item_data import ItemEntry

RANK_OPTIONS = ["E", "D", "C", "B", "A", "S"]


class ItemEditor(QWidget):
    """Editor panel for a single item's properties.

    Emits field_changed(iid, field_name, new_value) when a value is modified.
    """

    field_changed = Signal(str, str, object)  # (iid, field_name, new_value)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_item: ItemEntry | None = None
        self._item_edits: dict[str, dict] = {}
        self._loading = False  # suppress signals during population

        self._build_ui()
        self.setMinimumWidth(280)
        self.setEnabled(False)

    def set_item_edits(self, item_edits: dict[str, dict]):
        """Set the reference to the project's item_edits dict."""
        self._item_edits = item_edits

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---- Header ----
        self._name_label = QLabel()
        self._name_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        self._iid_label = QLabel()
        self._iid_label.setStyleSheet("color: gray; font-size: 11px;")
        layout.addWidget(self._name_label)
        layout.addWidget(self._iid_label)

        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        layout.addWidget(separator)

        # ---- Combat Stats ----
        combat_group = QGroupBox("Combat Stats")
        combat_grid = QGridLayout(combat_group)

        self._might_spin = self._add_spin_row(combat_grid, 0, "Might", 0, 255)
        self._accuracy_spin = self._add_spin_row(combat_grid, 1, "Accuracy", 0, 255)
        self._critical_spin = self._add_spin_row(combat_grid, 2, "Critical", 0, 255)
        self._weight_spin = self._add_spin_row(combat_grid, 3, "Weight", 0, 255)
        self._uses_spin = self._add_spin_row(combat_grid, 4, "Uses", 0, 255)
        self._wexp_spin = self._add_spin_row(combat_grid, 5, "WExp Gain", 0, 255)

        layout.addWidget(combat_group)

        # ---- Economy ----
        econ_group = QGroupBox("Economy")
        econ_grid = QGridLayout(econ_group)

        self._price_spin = self._add_spin_row(econ_grid, 0, "Price", 0, 65535)

        layout.addWidget(econ_group)

        # ---- Classification ----
        class_group = QGroupBox("Classification")
        class_grid = QGridLayout(class_group)

        class_grid.addWidget(QLabel("Weapon Type"), 0, 0)
        self._type_label = QLabel("-")
        class_grid.addWidget(self._type_label, 0, 1)

        class_grid.addWidget(QLabel("Weapon Rank"), 1, 0)
        self._rank_combo = QComboBox()
        self._rank_combo.addItems(RANK_OPTIONS)
        self._rank_combo.currentTextChanged.connect(
            lambda val: self._on_field_changed("weapon_rank", val)
        )
        class_grid.addWidget(self._rank_combo, 1, 1)

        layout.addWidget(class_group)

        # ---- Stretch ----
        layout.addStretch()

        # ---- Footer ----
        self._reset_btn = QPushButton("Reset to Original")
        self._reset_btn.clicked.connect(self._on_reset)
        layout.addWidget(self._reset_btn)

    def _add_spin_row(self, grid: QGridLayout, row: int, label: str,
                      min_val: int, max_val: int) -> QSpinBox:
        """Add a labeled spin box row to a grid layout and return the spin box."""
        grid.addWidget(QLabel(label), row, 0)
        spin = QSpinBox()
        spin.setRange(min_val, max_val)
        grid.addWidget(spin, row, 1)

        # Map spin boxes to field names via the label
        field_map = {
            "Might": "might",
            "Accuracy": "accuracy",
            "Critical": "critical",
            "Weight": "weight",
            "Uses": "uses",
            "WExp Gain": "wexp_gain",
            "Price": "price",
        }
        field_name = field_map.get(label, label.lower())
        spin.valueChanged.connect(
            lambda val, fn=field_name: self._on_field_changed(fn, val)
        )
        return spin

    def load_item(self, item: ItemEntry | None):
        """Populate the editor with an item's data."""
        self._loading = True
        self._current_item = item

        if item is None:
            self.setEnabled(False)
            self._name_label.setText("")
            self._iid_label.setText("")
            self._loading = False
            return

        self.setEnabled(True)
        edits = self._item_edits.get(item.iid, {})

        self._name_label.setText(item.display_name)
        self._iid_label.setText(item.iid)

        self._might_spin.setValue(edits.get("might", item.might))
        self._accuracy_spin.setValue(edits.get("accuracy", item.accuracy))
        self._critical_spin.setValue(edits.get("critical", item.critical))
        self._weight_spin.setValue(edits.get("weight", item.weight))
        self._uses_spin.setValue(edits.get("uses", item.uses))
        self._wexp_spin.setValue(edits.get("wexp_gain", item.wexp_gain))
        self._price_spin.setValue(edits.get("price", item.price))

        self._type_label.setText(item.weapon_type or "-")

        rank = edits.get("weapon_rank", item.weapon_rank)
        idx = self._rank_combo.findText(rank)
        if idx >= 0:
            self._rank_combo.setCurrentIndex(idx)

        self._loading = False

    def _on_field_changed(self, field_name: str, value):
        """Handle a field value change from a spin box or combo box."""
        if self._loading or self._current_item is None:
            return
        self.field_changed.emit(self._current_item.iid, field_name, value)

    def _on_reset(self):
        """Reset the current item to its original values."""
        if self._current_item is None:
            return
        iid = self._current_item.iid
        if iid in self._item_edits:
            del self._item_edits[iid]
        # Re-populate from originals
        self.load_item(self._current_item)
        # Emit changes so the table refreshes
        self.field_changed.emit(iid, "__reset__", None)
