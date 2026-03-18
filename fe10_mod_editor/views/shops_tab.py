"""Shops tab — chapter list with two-column inventory editor."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QTreeWidget, QTreeWidgetItem, QPushButton, QLabel,
)
from PySide6.QtCore import Qt

from fe10_mod_editor.models.item_data import ItemDatabase
from fe10_mod_editor.models.shop_data import ShopDatabase
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.widgets.shop_inventory import ShopInventoryWidget

PART_GROUPS = {
    "Part 1 \u2014 Dawn Brigade": [
        "C0000", "C0101", "C0102", "C0103", "C0104", "C0105",
        "C0106", "C0107", "C0108", "C0109", "C0110", "C0111",
    ],
    "Part 2 \u2014 Crimean Army": [
        "C0201", "C0202", "C0203", "C0204", "C0205",
    ],
    "Part 3 \u2014 Laguz Alliance": [
        "C0301", "C0302", "C0303", "C0304", "C0305", "C0306", "C0307",
        "C0308", "C0309", "C0310", "C0311", "C0312", "C0313", "C0314", "C0315",
    ],
    "Part 4 \u2014 Gods & Men": [
        "C0401", "C0402", "C0403", "C0404", "C0405", "C0406",
        "C0407a", "C0407b", "C0407c", "C0407d", "C0407e",
    ],
    "Tutorials": ["T01", "T02", "T03", "T04"],
}

DIFFICULTIES = ["normal", "hard", "maniac"]


class ShopsTab(QWidget):
    """Shops tab with chapter tree, difficulty selector, and two inventory panels."""

    def __init__(self, project: ProjectFile, parent=None):
        super().__init__(parent)
        self.project = project
        self.item_database: ItemDatabase | None = None
        self.shop_database: ShopDatabase | None = None

        self._current_chapter: str | None = None
        self._current_difficulty: str | None = None  # None = "All" (unified)

        self._difficulty_buttons: dict[str | None, QPushButton] = {}

        self._build_ui()
        self._connect_signals()

    def set_data(self, item_database: ItemDatabase | None,
                 shop_database: ShopDatabase | None):
        """Called when a project is loaded to supply data sources."""
        self.item_database = item_database
        self.shop_database = shop_database
        # Reload if a chapter was already selected
        if self._current_chapter:
            self._load_chapter(self._current_chapter)

    def _build_ui(self):
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)

        # ---- Top bar: difficulty selector ----
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(8, 4, 8, 4)

        top_bar.addWidget(QLabel("Difficulty:"))

        for label, key in [("All", None), ("Normal", "normal"),
                           ("Hard", "hard"), ("Maniac", "maniac")]:
            btn = QPushButton(label)
            btn.setCheckable(True)
            btn.setMaximumWidth(80)
            btn.clicked.connect(
                lambda checked, k=key: self._on_difficulty_changed(k)
            )
            top_bar.addWidget(btn)
            self._difficulty_buttons[key] = btn

        # Default to "All"
        self._difficulty_buttons[None].setChecked(True)
        top_bar.addStretch()
        outer.addLayout(top_bar)

        # ---- Main splitter: tree | inventory panels ----
        splitter = QSplitter(Qt.Horizontal)

        # Left sidebar: chapter tree
        self._chapter_tree = QTreeWidget()
        self._chapter_tree.setHeaderHidden(True)
        self._chapter_tree.setMinimumWidth(180)
        self._populate_chapter_tree()
        splitter.addWidget(self._chapter_tree)

        # Center: two inventory widgets side by side
        center = QWidget()
        center_layout = QHBoxLayout(center)
        center_layout.setContentsMargins(4, 4, 4, 4)

        self._weapon_shop = ShopInventoryWidget("Weapon Shop")
        self._item_shop = ShopInventoryWidget("Item Shop")

        center_layout.addWidget(self._weapon_shop)
        center_layout.addWidget(self._item_shop)

        splitter.addWidget(center)
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)

        outer.addWidget(splitter)

    def _populate_chapter_tree(self):
        """Build the chapter tree with Part group headers."""
        for group_name, chapters in PART_GROUPS.items():
            group_item = QTreeWidgetItem(self._chapter_tree, [group_name])
            group_item.setFlags(Qt.ItemIsEnabled)  # not selectable
            for ch_id in chapters:
                ch_item = QTreeWidgetItem(group_item, [ch_id])
                ch_item.setData(0, Qt.UserRole, ch_id)
            group_item.setExpanded(True)

    def _connect_signals(self):
        self._chapter_tree.currentItemChanged.connect(self._on_chapter_selected)
        self._weapon_shop.inventory_changed.connect(self._on_weapon_inventory_changed)
        self._item_shop.inventory_changed.connect(self._on_item_inventory_changed)

    # ------------------------------------------------------------------
    # Difficulty selector
    # ------------------------------------------------------------------

    def _on_difficulty_changed(self, difficulty: str | None):
        """Handle difficulty button click."""
        self._current_difficulty = difficulty
        for key, btn in self._difficulty_buttons.items():
            btn.setChecked(key == difficulty)
        if self._current_chapter:
            self._load_chapter(self._current_chapter)

    # ------------------------------------------------------------------
    # Chapter selection
    # ------------------------------------------------------------------

    def _on_chapter_selected(self, current: QTreeWidgetItem | None,
                             previous: QTreeWidgetItem | None):
        """Handle chapter tree selection."""
        if current is None:
            return
        ch_id = current.data(0, Qt.UserRole)
        if ch_id is None:
            # Group header selected, not a chapter
            return
        self._current_chapter = ch_id
        self._load_chapter(ch_id)

    def _load_chapter(self, chapter: str):
        """Load the shop inventory for the given chapter into both panels."""
        if self.item_database is None or self.shop_database is None:
            return

        # Resolve the inventory using the selected difficulty
        # For "All" mode we resolve using "normal" as the base view,
        # but edits are written to unified.
        resolve_diff = self._current_difficulty or "normal"
        resolved = self.shop_database.resolve(chapter, resolve_diff)

        weapon_iids = resolved["weapons"]
        item_iids = resolved["items"]

        self._weapon_shop.set_items(
            self.item_database.weapon_shop_items, weapon_iids
        )
        self._item_shop.set_items(
            self.item_database.item_shop_items, item_iids
        )

    # ------------------------------------------------------------------
    # Inventory change handlers
    # ------------------------------------------------------------------

    def _on_weapon_inventory_changed(self, iid_list: list[str]):
        """Handle weapon shop inventory change."""
        if self._current_chapter is None:
            return
        self._save_inventory("weapons", iid_list)

    def _on_item_inventory_changed(self, iid_list: list[str]):
        """Handle item shop inventory change."""
        if self._current_chapter is None:
            return
        self._save_inventory("items", iid_list)

    def _save_inventory(self, shop_type: str, iid_list: list[str]):
        """Write the changed inventory to the project and shop database."""
        chapter = self._current_chapter
        if chapter is None or self.shop_database is None:
            return

        if self._current_difficulty is None:
            # "All" mode -> unified edits
            if shop_type == "weapons":
                self.shop_database.set_unified(chapter, weapons=iid_list)
            else:
                self.shop_database.set_unified(chapter, items=iid_list)
            # Mirror to project
            if chapter not in self.project.shop_edits["unified"]:
                self.project.shop_edits["unified"][chapter] = {}
            self.project.shop_edits["unified"][chapter][shop_type] = iid_list
        else:
            # Specific difficulty -> override
            diff = self._current_difficulty
            if shop_type == "weapons":
                self.shop_database.set_override(chapter, diff, weapons=iid_list)
            else:
                self.shop_database.set_override(chapter, diff, items=iid_list)
            # Mirror to project
            if diff not in self.project.shop_edits["overrides"]:
                self.project.shop_edits["overrides"][diff] = {}
            if chapter not in self.project.shop_edits["overrides"][diff]:
                self.project.shop_edits["overrides"][diff][chapter] = {}
            self.project.shop_edits["overrides"][diff][chapter][shop_type] = iid_list
