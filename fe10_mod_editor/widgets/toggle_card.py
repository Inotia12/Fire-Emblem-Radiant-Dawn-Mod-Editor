"""Toggle card widget — a labeled on/off switch with description and affected count."""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QLabel, QCheckBox
from PySide6.QtCore import Signal


class ToggleCard(QFrame):
    toggled = Signal(str, bool)  # (toggle_key, new_state)

    def __init__(self, key: str, title: str, description: str, affected_count: int, parent=None):
        super().__init__(parent)
        self.key = key
        self.setFrameStyle(QFrame.Box | QFrame.Plain)

        layout = QHBoxLayout(self)

        text_layout = QVBoxLayout()
        title_label = QLabel(f"<b>{title}</b>")
        desc_label = QLabel(description)
        desc_label.setWordWrap(True)
        self.count_label = QLabel(f"Affects {affected_count} items")
        text_layout.addWidget(title_label)
        text_layout.addWidget(desc_label)
        text_layout.addWidget(self.count_label)

        self.checkbox = QCheckBox()
        self.checkbox.stateChanged.connect(self._on_toggle)

        layout.addLayout(text_layout, stretch=1)
        layout.addWidget(self.checkbox)

    def _on_toggle(self, state):
        self.toggled.emit(self.key, self.checkbox.isChecked())

    def set_checked(self, checked: bool):
        self.checkbox.setChecked(checked)
