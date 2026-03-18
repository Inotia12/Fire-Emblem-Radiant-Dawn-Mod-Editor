"""Main application window for the FE10 Mod Editor."""

import os

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QLabel, QVBoxLayout, QHBoxLayout,
    QToolBar, QStatusBar, QFileDialog, QMessageBox, QPushButton,
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.models.item_data import ItemDatabase
from fe10_mod_editor.models.shop_data import ShopDatabase
from fe10_mod_editor.models.character_data import CharacterDatabase
from fe10_mod_editor.models.class_data import ClassDatabase
from fe10_mod_editor.models.skill_data import SkillDatabase
from fe10_mod_editor.views.misc_tab import MiscTab
from fe10_mod_editor.views.items_tab import ItemsTab
from fe10_mod_editor.views.shops_tab import ShopsTab
from fe10_mod_editor.views.characters_tab import CharactersTab
from fe10_mod_editor.views.build_tab import FilesTab


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectFile = ProjectFile.new()
        self.project_path: str | None = None
        self.item_database: ItemDatabase | None = None
        self.shop_database: ShopDatabase | None = None
        self.character_database: CharacterDatabase | None = None
        self.class_database: ClassDatabase | None = None
        self.skill_database: SkillDatabase | None = None
        self._decompressed_fe10data: bytes | None = None

        self.setWindowTitle("FE10 Mod Editor")
        self.setMinimumSize(1200, 800)

        self._build_menu_bar()
        self._build_toolbar()
        self._build_central_area()
        self._build_status_bar()

    # ------------------------------------------------------------------
    # Construction helpers
    # ------------------------------------------------------------------

    def _build_menu_bar(self):
        menu_bar = self.menuBar()

        # File menu
        file_menu = menu_bar.addMenu("&File")

        new_action = QAction("&New Project", self)
        new_action.setShortcut(QKeySequence("Ctrl+N"))
        new_action.triggered.connect(self._on_new)
        file_menu.addAction(new_action)

        open_action = QAction("&Open Project\u2026", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As\u2026", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        # Empty stub menus removed (Edit, Tools, Help had no entries)

    def _build_toolbar(self):
        toolbar = QToolBar("Main Toolbar", self)
        toolbar.setMovable(False)
        self.addToolBar(toolbar)

        open_btn = QAction("Open Project", self)
        open_btn.triggered.connect(self._on_open)
        toolbar.addAction(open_btn)

        save_btn = QAction("Save", self)
        save_btn.triggered.connect(self._on_save)
        toolbar.addAction(save_btn)

        toolbar.addSeparator()

        self._project_name_label = QLabel("  No project loaded")
        toolbar.addWidget(self._project_name_label)

    def _build_central_area(self):
        """Build the central widget: tab bar on top, persistent Build button at bottom."""
        central = QWidget(self)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        # Tab widget
        self._tabs = QTabWidget()
        layout.addWidget(self._tabs, stretch=1)

        # Files tab (first tab — entry point)
        self._files_tab = FilesTab(self.project)
        self._files_tab.game_directory_ready.connect(self._on_game_directory_ready)
        self._tabs.addTab(self._files_tab, "Files")

        # Items tab
        self._items_tab = ItemsTab(self.project, self.item_database)
        self._tabs.addTab(self._items_tab, "Items")

        # Shops tab
        self._shops_tab = ShopsTab(self.project)
        self._tabs.addTab(self._shops_tab, "Shops")

        # Characters tab
        self._characters_tab = CharactersTab(self.project)
        self._tabs.addTab(self._characters_tab, "Characters")

        # Misc tab
        self._misc_tab = MiscTab(self.project)
        self._tabs.addTab(self._misc_tab, "Misc")

        self._tabs.currentChanged.connect(self._on_tab_changed)

        # Persistent Build button bar (always visible below tabs)
        build_bar = QHBoxLayout()
        build_bar.setContentsMargins(8, 4, 8, 4)
        build_bar.addStretch()
        self._build_btn = QPushButton("Build Mod")
        self._build_btn.setFixedHeight(48)
        self._build_btn.setMinimumWidth(200)
        self._build_btn.setStyleSheet("font-size: 15px; font-weight: bold;")
        self._build_btn.clicked.connect(self._on_build)
        build_bar.addWidget(self._build_btn)
        build_bar.addStretch()
        layout.addLayout(build_bar)

        self.setCentralWidget(central)

    def _build_status_bar(self):
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # File menu actions
    # ------------------------------------------------------------------

    def _on_new(self):
        self.project = ProjectFile.new()
        self.project_path = None
        self.item_database = None
        self.shop_database = None
        self.character_database = None
        self.class_database = None
        self.skill_database = None
        self._decompressed_fe10data = None
        self._refresh_items_tab()
        self._refresh_shops_tab()
        self._refresh_characters_tab()
        self._refresh_misc_tab()
        self._refresh_files_tab()
        self._project_name_label.setText("  New project")
        self.statusBar().showMessage("New project created.")

    def _on_open(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            "",
            "FE10 Mod Files (*.fe10mod);;All Files (*)",
        )
        if not path:
            return
        try:
            self.project = ProjectFile.load(path)
            self.project_path = path
            self._load_item_database()
            self._load_shop_database()
            self._load_character_data()
            self._refresh_items_tab()
            self._refresh_shops_tab()
            self._refresh_characters_tab()
            self._refresh_misc_tab()
            self._refresh_files_tab()
            self._project_name_label.setText(f"  {path}")
            self._update_status_bar_counts()
        except Exception as exc:
            QMessageBox.critical(self, "Open Failed", str(exc))

    def _on_save(self):
        if self.project_path is None:
            self._on_save_as()
            return
        try:
            self.project.save(self.project_path)
            self.statusBar().showMessage(f"Saved: {self.project_path}")
        except Exception as exc:
            QMessageBox.critical(self, "Save Failed", str(exc))

    def _on_save_as(self):
        path, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            "",
            "FE10 Mod Files (*.fe10mod);;All Files (*)",
        )
        if not path:
            return
        self.project_path = path
        self._project_name_label.setText(f"  {path}")
        self._on_save()

    # ------------------------------------------------------------------
    # Game directory auto-detection callback
    # ------------------------------------------------------------------

    def _on_game_directory_ready(self, game_dir: str):
        """Called when the Files tab validates the game directory and backups are ready."""
        self._load_item_database()
        self._load_shop_database()
        self._load_character_data()
        self._refresh_items_tab()
        self._refresh_shops_tab()
        self._refresh_characters_tab()
        self._update_status_bar_counts()

    # ------------------------------------------------------------------
    # Build button
    # ------------------------------------------------------------------

    def _on_build(self):
        """Start a build via the persistent Build button."""
        self._build_btn.setEnabled(False)
        # Switch to Files tab so user can see the build log
        self._tabs.setCurrentWidget(self._files_tab)

        worker = self._files_tab.start_build()
        if worker:
            worker.finished_ok.connect(self._on_build_finished)
            worker.finished_error.connect(self._on_build_finished)

    def _on_build_finished(self, *args):
        self._build_btn.setEnabled(True)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_item_database(self):
        """Decompress FE10Data.cms from backup_dir and build ItemDatabase."""
        from fe10_mod_editor.core.lz10 import decompress_lz10
        from fe10_mod_editor.core.item_parser import parse_all_items

        backup_dir = self.project.paths.get("backup_dir", "")
        if not backup_dir:
            self.item_database = None
            self._decompressed_fe10data = None
            return

        cms_path = os.path.join(backup_dir, "FE10Data.cms")
        if not os.path.isfile(cms_path):
            self.item_database = None
            self._decompressed_fe10data = None
            return

        with open(cms_path, "rb") as f:
            compressed = f.read()

        # FE10Data.cms is LZ10-compressed; decompress before parsing
        data = decompress_lz10(compressed)
        self._decompressed_fe10data = data
        parsed = parse_all_items(data)
        self.item_database = ItemDatabase.from_parsed_items(parsed)

    def _load_shop_database(self):
        """Parse a vanilla shop file from backup_dir and build ShopDatabase."""
        backup_dir = self.project.paths.get("backup_dir", "")
        if not backup_dir:
            self.shop_database = None
            return

        # Try normal difficulty shop file first, fall back to others
        shop_path = None
        for filename in ("shopitem_n.bin", "shopitem_h.bin", "shopitem_m.bin"):
            candidate = os.path.join(backup_dir, filename)
            if os.path.isfile(candidate):
                shop_path = candidate
                break

        if shop_path is None:
            self.shop_database = None
            return

        from fe10_mod_editor.core.shop_parser import parse_shop_file
        parsed = parse_shop_file(shop_path)

        vanilla_weapons = parsed["wshop_items"]
        vanilla_items = parsed["ishop_items"]
        self.shop_database = ShopDatabase(vanilla_weapons, vanilla_items)

        # Apply saved project edits
        self.shop_database.load_from_dict(self.project.shop_edits)

    def _refresh_shops_tab(self):
        """Update the Shops tab with current data sources."""
        self._shops_tab.project = self.project
        self._shops_tab.set_data(self.item_database, self.shop_database)

    def _refresh_items_tab(self):
        """Update the Items tab with current project and item database."""
        self._items_tab.set_data_source(self.item_database, self.project)

    def _refresh_misc_tab(self):
        """Replace the Misc tab widget after a project reload."""
        misc_index = 4  # Files=0, Items=1, Shops=2, Characters=3, Misc=4
        self._misc_tab = MiscTab(self.project)
        self._tabs.removeTab(misc_index)
        self._tabs.insertTab(misc_index, self._misc_tab, "Misc")
        self._tabs.setCurrentIndex(misc_index)

    def _refresh_characters_tab(self):
        """Update the Characters tab with current data sources."""
        self._characters_tab.set_data(
            self.character_database, self.class_database,
            self.skill_database, self.project,
        )

    def _load_character_data(self):
        """Parse characters, classes, and skills from cached decompressed FE10Data."""
        if self._decompressed_fe10data is None:
            self.character_database = None
            self.class_database = None
            self.skill_database = None
            return

        from fe10_mod_editor.core.character_parser import parse_all_characters
        from fe10_mod_editor.core.class_parser import parse_all_classes
        from fe10_mod_editor.core.skill_parser import parse_all_skills

        data = self._decompressed_fe10data
        parsed_chars = parse_all_characters(data)
        parsed_classes = parse_all_classes(data)
        parsed_skills = parse_all_skills(data)

        self.character_database = CharacterDatabase.from_parsed(parsed_chars)
        self.class_database = ClassDatabase.from_parsed(parsed_classes)
        self.skill_database = SkillDatabase.from_parsed(parsed_skills)

    def _refresh_files_tab(self):
        """Sync files tab paths and refresh summary counts."""
        self._files_tab.project = self.project
        self._files_tab._game_dir_edit.setText(self.project.paths.get("game_dir", ""))
        self._files_tab._refresh_validation()
        self._files_tab.refresh_summary()

    def _update_status_bar_counts(self):
        """Update status bar with item count and modified count."""
        item_count = self.item_database.count if self.item_database else 0
        modified_count = len(self.project.item_edits)
        self.statusBar().showMessage(
            f"Loaded {item_count} items | {modified_count} modified"
        )

    def _on_tab_changed(self, index: int):
        """Refresh files tab summary when switching to it."""
        files_index = 0  # Files=0, Items=1, Shops=2, Characters=3, Misc=4
        if index == files_index:
            self._files_tab.refresh_summary()
