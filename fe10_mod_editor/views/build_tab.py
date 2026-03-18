"""Files tab — game directory selection, backup management, build log, and restore.

Formerly the "Build" tab. Now the entry-point tab where the user points at
their game directory and the app auto-detects / creates backups.
"""

import os
import shutil

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


# Signal emitted when game directory is validated and data should be loaded.
# The MainWindow connects to this to trigger item/shop database loading.


class FilesTab(QWidget):
    """Files tab: game directory, backup verification, change summary, build log."""

    # Emitted when the game directory is validated and backups are ready.
    # The MainWindow should connect to this to reload databases and refresh tabs.
    game_directory_ready = Signal(str)  # emits the game_dir path

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
        heading = QLabel("Game Directory")
        heading.setStyleSheet("font-weight: bold; font-size: 13px;")
        layout.addWidget(heading)

        # Game Directory row (the only path the user needs to set)
        game_row = QHBoxLayout()
        game_label = QLabel("Game Directory:")
        game_label.setFixedWidth(130)
        self._game_dir_edit = QLineEdit()
        self._game_dir_edit.setPlaceholderText("Select game DATA directory (e.g. .../Game/DATA)")
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
        self._validation_label = QLabel("No game directory selected")
        self._validation_label.setStyleSheet("color: gray;")
        layout.addWidget(self._validation_label)

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

    def _browse_game_dir(self):
        path = QFileDialog.getExistingDirectory(self, "Select Game DATA Directory")
        if path:
            self._game_dir_edit.setText(path)

    def _on_game_dir_changed(self, text: str):
        self.project.paths["game_dir"] = text
        self._auto_detect_and_load(text)

    def _auto_detect_and_load(self, game_dir: str):
        """Validate game directory, auto-create/verify backup, emit ready signal."""
        if not game_dir or not os.path.isdir(game_dir):
            self._validation_label.setText("No game directory selected")
            self._validation_label.setStyleSheet("color: gray;")
            return

        # Check for expected game files
        expected_files = {
            "FE10Data.cms": os.path.join(game_dir, "files", "FE10Data.cms"),
            "shopitem_n.bin": os.path.join(game_dir, "files", "Shop", "shopitem_n.bin"),
            "shopitem_m.bin": os.path.join(game_dir, "files", "Shop", "shopitem_m.bin"),
            "shopitem_h.bin": os.path.join(game_dir, "files", "Shop", "shopitem_h.bin"),
            "fst.bin": os.path.join(game_dir, "sys", "fst.bin"),
        }

        missing = [name for name, path in expected_files.items() if not os.path.isfile(path)]
        if missing:
            self._validation_label.setText(f"Missing game files: {', '.join(missing)}")
            self._validation_label.setStyleSheet("color: red;")
            return

        # Derive backup directory as sibling of game_dir
        # e.g. game_dir = .../Game/DATA  =>  backup_dir = .../Backup
        backup_dir = os.path.join(os.path.dirname(game_dir), "Backup")
        self.project.paths["backup_dir"] = backup_dir

        try:
            self._ensure_backup(backup_dir, expected_files)
        except Exception as exc:
            self._validation_label.setText(f"Backup error: {exc}")
            self._validation_label.setStyleSheet("color: red;")
            return

        self._validation_label.setText(f"Backup verified ({backup_dir})")
        self._validation_label.setStyleSheet("color: green;")

        # Signal the main window to load databases
        self.game_directory_ready.emit(game_dir)

    def _ensure_backup(self, backup_dir: str, expected_files: dict[str, str]):
        """Create backup directory if needed, copy originals, compute/verify hashes."""
        from fe10_mod_editor.core.backup_manager import (
            compute_backup_hashes, verify_backup_hashes, BACKUP_FILES,
        )

        if not os.path.isdir(backup_dir):
            # First time: create backup directory and copy files
            os.makedirs(backup_dir, exist_ok=True)
            for fname in BACKUP_FILES:
                src = expected_files[fname]
                dst = os.path.join(backup_dir, fname)
                shutil.copy2(src, dst)

            # Compute and store hashes
            hashes = compute_backup_hashes(backup_dir)
            self.project.backup_hashes = hashes
        else:
            # Backup exists — check if we have stored hashes
            if not self.project.backup_hashes:
                # Compute hashes from existing backup
                hashes = compute_backup_hashes(backup_dir)
                self.project.backup_hashes = hashes
            else:
                # Verify stored hashes match backup files
                result = verify_backup_hashes(backup_dir, self.project.backup_hashes)
                if not result.ok:
                    raise RuntimeError(result.error)

    def _refresh_validation(self):
        """Re-run validation against current project state."""
        game_dir = self.project.paths.get("game_dir", "")
        self._auto_detect_and_load(game_dir)

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

    # ------------------------------------------------------------------
    # Build (called by main window's Build button)
    # ------------------------------------------------------------------

    def start_build(self):
        """Start a build. Called from the main window's persistent Build button."""
        self._log_view.clear()

        self._worker = BuildWorker(self.project)
        self._worker.log_message.connect(self._append_log)
        self._worker.finished_ok.connect(self._on_build_ok)
        self._worker.finished_error.connect(self._on_build_error)
        self._worker.start()
        return self._worker  # So main window can disable/enable its button

    def _append_log(self, message: str):
        self._log_view.appendPlainText(message)

    def _on_build_ok(self):
        self._append_log("--- Build succeeded ---")
        self._status_bar_message("Build completed successfully.")

    def _on_build_error(self, error: str):
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


# Keep backward-compatible alias so existing imports work
BuildTab = FilesTab
