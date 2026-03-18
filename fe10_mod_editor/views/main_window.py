"""Main application window for the FE10 Mod Editor."""

from PySide6.QtWidgets import (
    QMainWindow, QTabWidget, QWidget, QLabel,
    QToolBar, QStatusBar, QFileDialog, QMessageBox,
)
from PySide6.QtGui import QAction, QKeySequence
from PySide6.QtCore import Qt

from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.views.misc_tab import MiscTab


class MainWindow(QMainWindow):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.project: ProjectFile = ProjectFile.new()
        self.project_path: str | None = None

        self.setWindowTitle("FE10 Mod Editor")
        self.setMinimumSize(1200, 800)

        self._build_menu_bar()
        self._build_toolbar()
        self._build_tabs()
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

        open_action = QAction("&Open Project…", self)
        open_action.setShortcut(QKeySequence("Ctrl+O"))
        open_action.triggered.connect(self._on_open)
        file_menu.addAction(open_action)

        file_menu.addSeparator()

        save_action = QAction("&Save", self)
        save_action.setShortcut(QKeySequence("Ctrl+S"))
        save_action.triggered.connect(self._on_save)
        file_menu.addAction(save_action)

        save_as_action = QAction("Save &As…", self)
        save_as_action.setShortcut(QKeySequence("Ctrl+Shift+S"))
        save_as_action.triggered.connect(self._on_save_as)
        file_menu.addAction(save_as_action)

        # Edit menu (stub)
        menu_bar.addMenu("&Edit")

        # Tools menu (stub)
        menu_bar.addMenu("&Tools")

        # Help menu (stub)
        menu_bar.addMenu("&Help")

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

    def _build_tabs(self):
        self._tabs = QTabWidget(self)
        self.setCentralWidget(self._tabs)

        # Items tab — placeholder
        self._tabs.addTab(QWidget(), "Items")

        # Shops tab — placeholder
        self._tabs.addTab(QWidget(), "Shops")

        # Build tab — placeholder
        self._tabs.addTab(QWidget(), "Build")

        # Misc tab — fully implemented
        self._misc_tab = MiscTab(self.project)
        self._tabs.addTab(self._misc_tab, "Misc")

    def _build_status_bar(self):
        self.statusBar().showMessage("Ready")

    # ------------------------------------------------------------------
    # File menu actions
    # ------------------------------------------------------------------

    def _on_new(self):
        self.project = ProjectFile.new()
        self.project_path = None
        self._refresh_misc_tab()
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
            self._refresh_misc_tab()
            self._project_name_label.setText(f"  {path}")
            self.statusBar().showMessage(f"Opened: {path}")
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
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_misc_tab(self):
        """Replace the Misc tab widget after a project reload."""
        misc_index = 3  # Items=0, Shops=1, Build=2, Misc=3
        self._misc_tab = MiscTab(self.project)
        self._tabs.removeTab(misc_index)
        self._tabs.insertTab(misc_index, self._misc_tab, "Misc")
        self._tabs.setCurrentIndex(misc_index)
