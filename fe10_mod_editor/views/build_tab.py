"""Build tab — build configuration, execution, and log output."""

from PySide6.QtCore import QThread, Signal, Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter,
    QLabel, QLineEdit, QPushButton, QPlainTextEdit,
    QFileDialog, QMessageBox, QSizePolicy,
)

from fe10_mod_editor.models.project import ProjectFile


class BuildWorker(QThread):
    log_message = Signal(str)
    finished_ok = Signal()
    finished_error = Signal(str)

    def __init__(self, project: ProjectFile):
        super().__init__()
        self.project = project

    def run(self):
        try:
            from fe10_mod_editor.models.mod_builder import ModBuilder
            builder = ModBuilder(self.project, log_callback=self.log_message.emit)
            builder.build()
            self.finished_ok.emit()
        except Exception as e:
            self.finished_error.emit(str(e))


class BuildTab(QWidget):
    def __init__(self, project: ProjectFile, parent=None):
        super().__init__(parent)
        self.project = project
        self._worker: BuildWorker | None = None

        self._build_ui()
        self.refresh_summary()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        root_layout = QVBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Orientation.Horizontal, self)
        root_layout.addWidget(splitter)

        # Left panel
        left_widget = QWidget()
        left_widget.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Expanding)
        left_layout = QVBoxLayout(left_widget)
        left_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        self._add_paths_section(left_layout)
        left_layout.addSpacing(12)
        self._add_summary_section(left_layout)
        left_layout.addSpacing(12)
        self._add_build_button(left_layout)
        left_layout.addSpacing(12)
        self._add_danger_zone(left_layout)
        left_layout.addStretch()

        # Right panel — build log
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)

        log_heading = QLabel("Build Log")
        log_heading.setStyleSheet("font-weight: bold; font-size: 13px;")
        right_layout.addWidget(log_heading)

        self._log_view = QPlainTextEdit()
        self._log_view.setReadOnly(True)
        mono_font = QFont("Courier New", 9)
        mono_font.setStyleHint(QFont.StyleHint.Monospace)
        self._log_view.setFont(mono_font)
        right_layout.addWidget(self._log_view)

        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)

    def _add_paths_section(self, layout: QVBoxLayout):
        heading = QLabel("Paths")
        heading.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(heading)

        # Backup Directory row
        backup_row = QHBoxLayout()
        backup_label = QLabel("Backup Directory:")
        backup_label.setFixedWidth(130)
        self._backup_dir_edit = QLineEdit()
        self._backup_dir_edit.setPlaceholderText("Select backup directory…")
        self._backup_dir_edit.setText(self.project.paths.get("backup_dir", ""))
        self._backup_dir_edit.textChanged.connect(self._on_backup_dir_changed)
        backup_browse = QPushButton("Browse")
        backup_browse.setFixedWidth(70)
        backup_browse.clicked.connect(self._browse_backup_dir)
        backup_row.addWidget(backup_label)
        backup_row.addWidget(self._backup_dir_edit)
        backup_row.addWidget(backup_browse)
        layout.addLayout(backup_row)

        # Game Directory row
        game_row = QHBoxLayout()
        game_label = QLabel("Game Directory:")
        game_label.setFixedWidth(130)
        self._game_dir_edit = QLineEdit()
        self._game_dir_edit.setPlaceholderText("Select game directory…")
        self._game_dir_edit.setText(self.project.paths.get("game_dir", ""))
        self._game_dir_edit.textChanged.connect(self._on_game_dir_changed)
        game_browse = QPushButton("Browse")
        game_browse.setFixedWidth(70)
        game_browse.clicked.connect(self._browse_game_dir)
        game_row.addWidget(game_label)
        game_row.addWidget(self._game_dir_edit)
        game_row.addWidget(game_browse)
        layout.addLayout(game_row)

        # Validation indicator
        self._validation_label = QLabel("Backup not verified")
        self._validation_label.setStyleSheet("color: red;")
        layout.addWidget(self._validation_label)

        self._refresh_validation()

    def _add_summary_section(self, layout: QVBoxLayout):
        heading = QLabel("Change Summary")
        heading.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(heading)

        self._items_modified_label = QLabel("Items modified: 0")
        self._shops_customized_label = QLabel("Shops customized: 0")
        self._difficulty_overrides_label = QLabel("Difficulty overrides: 0")
        self._misc_toggles_label = QLabel("Misc toggles active: 0")

        layout.addWidget(self._items_modified_label)
        layout.addWidget(self._shops_customized_label)
        layout.addWidget(self._difficulty_overrides_label)
        layout.addWidget(self._misc_toggles_label)

    def _add_build_button(self, layout: QVBoxLayout):
        self._build_btn = QPushButton("Build Mod")
        self._build_btn.setFixedHeight(48)
        self._build_btn.setStyleSheet("font-size: 15px; font-weight: bold;")
        self._build_btn.clicked.connect(self._on_build)
        layout.addWidget(self._build_btn)

    def _add_danger_zone(self, layout: QVBoxLayout):
        danger_heading = QLabel("Danger Zone")
        danger_heading.setStyleSheet("font-weight: bold; font-size: 13px; color: red;")
        layout.addWidget(danger_heading)

        restore_btn = QPushButton("Restore Original Files from Backup")
        restore_btn.clicked.connect(self._on_restore)
        layout.addWidget(restore_btn)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _browse_backup_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Backup Directory")
        if path:
            self._backup_dir_edit.setText(path)

    def _browse_game_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Game Directory")
        if path:
            self._game_dir_edit.setText(path)

    def _on_backup_dir_changed(self, text: str):
        self.project.paths["backup_dir"] = text
        self._refresh_validation()

    def _on_game_dir_changed(self, text: str):
        self.project.paths["game_dir"] = text

    def _refresh_validation(self):
        """Check whether backup files are verified and update the indicator label."""
        from fe10_mod_editor.core.backup_manager import verify_backup_hashes
        stored = self.project.backup_hashes
        backup_dir = self.project.paths.get("backup_dir", "")

        if not stored or not backup_dir:
            self._validation_label.setText("Backup not verified")
            self._validation_label.setStyleSheet("color: red;")
            return

        result = verify_backup_hashes(backup_dir, stored)
        if result.ok:
            self._validation_label.setText("Backup files verified")
            self._validation_label.setStyleSheet("color: green;")
        else:
            self._validation_label.setText(f"Backup not verified: {result.error}")
            self._validation_label.setStyleSheet("color: red;")

    def refresh_summary(self):
        """Update change-count labels from current project state."""
        proj = self.project

        items_modified = len(proj.item_edits)

        unified = proj.shop_edits.get("unified", {})
        shops_customized = len(unified)

        overrides = proj.shop_edits.get("overrides", {})
        difficulty_overrides = sum(len(chapters) for chapters in overrides.values())

        weapon_changes = proj.misc.get("weapon_changes", {})
        misc_toggles = sum(1 for v in weapon_changes.values() if v is True)

        self._items_modified_label.setText(f"Items modified: {items_modified}")
        self._shops_customized_label.setText(f"Shops customized: {shops_customized}")
        self._difficulty_overrides_label.setText(f"Difficulty overrides: {difficulty_overrides}")
        self._misc_toggles_label.setText(f"Misc toggles active: {misc_toggles}")

    def _on_build(self):
        self._log_view.clear()
        self._build_btn.setEnabled(False)

        self._worker = BuildWorker(self.project)
        self._worker.log_message.connect(self._append_log)
        self._worker.finished_ok.connect(self._on_build_ok)
        self._worker.finished_error.connect(self._on_build_error)
        self._worker.start()

    def _append_log(self, message: str):
        self._log_view.appendPlainText(message)

    def _on_build_ok(self):
        self._build_btn.setEnabled(True)
        self._append_log("--- Build succeeded ---")
        self._status_bar_message("Build completed successfully.")

    def _on_build_error(self, error: str):
        self._build_btn.setEnabled(True)
        self._append_log(f"--- Build FAILED: {error} ---")
        self._status_bar_message(f"Build failed: {error}")

    def _on_restore(self):
        result = QMessageBox.warning(
            self,
            "Restore Backup",
            "This will overwrite game files with the original backup copies.\n\nAre you sure?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.Cancel,
            QMessageBox.StandardButton.Cancel,
        )
        if result != QMessageBox.StandardButton.Yes:
            return

        try:
            from fe10_mod_editor.core.backup_manager import restore_backup
            import os
            backup_dir = self.project.paths.get("backup_dir", "")
            game_dir = self.project.paths.get("game_dir", "")
            game_files = os.path.join(game_dir, "files")
            shop_dir = os.path.join(game_files, "Shop")
            fst_path = os.path.join(game_dir, "sys", "fst.bin")
            restored = restore_backup(backup_dir, game_files, shop_dir, fst_path)
            self._append_log(f"Restored {len(restored)} file(s) from backup.")
            self._status_bar_message("Original files restored from backup.")
        except Exception as exc:
            QMessageBox.critical(self, "Restore Failed", str(exc))

    def _status_bar_message(self, msg: str):
        """Post a message to the main window's status bar if available."""
        window = self.window()
        if hasattr(window, "statusBar"):
            window.statusBar().showMessage(msg)
