"""Characters tab — filterable character table with sub-tabbed editor panel."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QLabel,
    QLineEdit, QComboBox, QPushButton, QTableView, QAbstractItemView,
    QHeaderView, QTabWidget,
)
from PySide6.QtCore import Qt

from fe10_mod_editor.models.character_data import (
    CharacterDatabase, CharacterEntry, ALLIED_PIDS,
)
from fe10_mod_editor.models.class_data import ClassDatabase
from fe10_mod_editor.models.skill_data import SkillDatabase
from fe10_mod_editor.models.project import ProjectFile
from fe10_mod_editor.widgets.character_table import (
    CharacterTableModel, CharacterSortFilterProxy,
)
from fe10_mod_editor.widgets.character_stats_editor import CharacterStatsEditor
from fe10_mod_editor.widgets.character_growths_editor import CharacterGrowthsEditor
from fe10_mod_editor.widgets.character_skills_editor import CharacterSkillsEditor
from fe10_mod_editor.widgets.character_info_editor import CharacterInfoEditor

# Filter combo box options: (display text, filter key)
_FILTER_OPTIONS = [
    ("Allied", "allied"),
    ("All", "all"),
    ("Laguz", "laguz"),
    ("Beorc", "beorc"),
]


class CharactersTab(QWidget):
    """Main Characters tab with filter bar, sortable table, and sub-tabbed editor panel."""

    def __init__(self, project: ProjectFile,
                 char_db: CharacterDatabase | None = None,
                 class_db: ClassDatabase | None = None,
                 skill_db: SkillDatabase | None = None,
                 parent=None):
        super().__init__(parent)
        self.project = project
        self.char_db = char_db
        self.class_db = class_db
        self.skill_db = skill_db

        self._current_pid: str | None = None

        self._build_ui()
        self._connect_signals()

    def set_data(self, char_db: CharacterDatabase | None,
                 class_db: ClassDatabase | None,
                 skill_db: SkillDatabase | None,
                 project: ProjectFile):
        """Update the backing data and refresh all widgets."""
        self.char_db = char_db
        self.class_db = class_db
        self.skill_db = skill_db
        self.project = project

        self._model.set_data_source(char_db, class_db, project.character_edits)
        self._skills_editor.set_skill_database(skill_db)
        self._current_pid = None
        self._clear_editor()
        self._update_counter()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self):
        outer_layout = QVBoxLayout(self)
        outer_layout.setContentsMargins(0, 0, 0, 0)

        splitter = QSplitter(Qt.Horizontal)

        # ---- Left side: filter bar + table + counter ----
        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(4, 4, 4, 4)

        # Filter bar
        filter_bar = QHBoxLayout()

        self._search_input = QLineEdit()
        self._search_input.setPlaceholderText("Search characters...")
        self._search_input.setClearButtonEnabled(True)
        filter_bar.addWidget(self._search_input, stretch=1)

        self._filter_combo = QComboBox()
        for display_text, _key in _FILTER_OPTIONS:
            self._filter_combo.addItem(display_text, userData=_key)
        self._filter_combo.setCurrentIndex(0)  # Default to "Allied"
        self._filter_combo.setMinimumWidth(90)
        filter_bar.addWidget(self._filter_combo)

        left_layout.addLayout(filter_bar)

        # Character table
        self._model = CharacterTableModel(
            self.char_db, self.class_db, self.project.character_edits,
        )
        self._proxy = CharacterSortFilterProxy()
        self._proxy.setSourceModel(self._model)
        self._proxy.set_filter_type("allied")  # match default combo

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

        # Counter label
        self._counter_label = QLabel("")
        self._counter_label.setStyleSheet("color: gray; font-size: 11px;")
        left_layout.addWidget(self._counter_label)
        self._update_counter()

        # ---- Right side: header + sub-tabbed editors + reset button ----
        right_widget = QWidget()
        right_layout = QVBoxLayout(right_widget)
        right_layout.setContentsMargins(4, 4, 4, 4)

        # Header area
        self._header_name = QLabel("")
        self._header_name.setStyleSheet("font-size: 16px; font-weight: bold;")
        right_layout.addWidget(self._header_name)

        self._header_detail = QLabel("")
        self._header_detail.setStyleSheet("color: gray; font-size: 11px;")
        right_layout.addWidget(self._header_detail)

        # Sub-tab widget
        self._sub_tabs = QTabWidget()

        self._stats_editor = CharacterStatsEditor()
        self._sub_tabs.addTab(self._stats_editor, "Stats")

        self._growths_editor = CharacterGrowthsEditor()
        self._sub_tabs.addTab(self._growths_editor, "Growths")

        self._skills_editor = CharacterSkillsEditor()
        self._sub_tabs.addTab(self._skills_editor, "Skills")

        self._info_editor = CharacterInfoEditor()
        self._sub_tabs.addTab(self._info_editor, "Info")

        right_layout.addWidget(self._sub_tabs, stretch=1)

        # Reset button
        self._reset_btn = QPushButton("Reset to Original")
        self._reset_btn.setEnabled(False)
        right_layout.addWidget(self._reset_btn)

        # Assemble splitter
        splitter.addWidget(left_widget)
        splitter.addWidget(right_widget)
        splitter.setStretchFactor(0, 3)
        splitter.setStretchFactor(1, 2)

        outer_layout.addWidget(splitter)

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self):
        # Search text -> proxy filter
        self._search_input.textChanged.connect(self._proxy.set_search_text)

        # Filter combo -> proxy filter type
        self._filter_combo.currentIndexChanged.connect(self._on_filter_changed)

        # Table selection -> load character into editors
        self._table.selectionModel().currentRowChanged.connect(
            self._on_row_selected
        )

        # Editor field changes -> project edits
        self._stats_editor.field_changed.connect(self._on_field_changed)
        self._growths_editor.field_changed.connect(self._on_field_changed)
        self._skills_editor.field_changed.connect(self._on_field_changed)
        self._info_editor.field_changed.connect(self._on_field_changed)

        # Info editor class max stat changes -> project class_max_stat_edits
        self._info_editor.class_max_stats_changed.connect(
            self._on_class_max_stats_changed
        )

        # Reset button
        self._reset_btn.clicked.connect(self._on_reset)

        # Update counter when filter changes
        self._proxy.layoutChanged.connect(self._update_counter)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_filter_changed(self, index: int):
        """Handle filter combo box change."""
        filter_key = self._filter_combo.currentData()
        if filter_key:
            self._proxy.set_filter_type(filter_key)
        self._update_counter()

    def _on_row_selected(self, current, previous):
        """Handle table row selection — load character into all 4 editors."""
        if not current.isValid():
            self._clear_editor()
            return

        source_index = self._proxy.mapToSource(current)
        char = self._model.character_at_row(source_index.row())
        if char is None:
            self._clear_editor()
            return

        self._current_pid = char.pid
        self._load_character(char)

    def _load_character(self, char: CharacterEntry):
        """Load a character into the header and all 4 sub-tab editors."""
        class_entry = self.class_db.get(char.jid) if self.class_db else None
        edits = self.project.character_edits.get(char.pid, {})
        class_edits = self.project.class_max_stat_edits.get(char.jid, {})

        # Header
        class_name = class_entry.display_name if class_entry else char.jid
        level = edits.get("level", char.level)
        self._header_name.setText(char.display_name)
        self._header_detail.setText(f"{char.pid}  |  {class_name} Lv {level}")

        # Editors
        self._stats_editor.load_character(char, class_entry, edits)
        self._growths_editor.load_character(char, class_entry, edits)
        self._skills_editor.load_character(
            char, class_entry, self.skill_db, edits
        )
        self._info_editor.load_character(
            char, class_entry, edits, class_edits, self.project.misc
        )

        self._reset_btn.setEnabled(True)

    def _clear_editor(self):
        """Clear the editor panel when no character is selected."""
        self._current_pid = None
        self._header_name.setText("")
        self._header_detail.setText("Select a character to edit")
        self._stats_editor.setEnabled(False)
        self._growths_editor.setEnabled(False)
        self._skills_editor.setEnabled(False)
        self._info_editor.setEnabled(False)
        self._reset_btn.setEnabled(False)

    def _on_field_changed(self, pid: str, field_path: str, value):
        """Handle a field change from any editor — store in project.character_edits."""
        if self.char_db is None:
            return
        char = self.char_db.get(pid)
        if char is None:
            return

        # Determine the original value for comparison
        original = self._get_original_value(char, field_path)

        # Compare with original and store/remove edit
        if value == original:
            self._remove_edit(pid, field_path)
        else:
            self._store_edit(pid, field_path, value)

        self._model.refresh()

    def _get_original_value(self, char: CharacterEntry, field_path: str):
        """Get the original (unedited) value for a given field path."""
        if field_path == "level":
            return char.level
        elif field_path == "authority_stars":
            return char.authority_stars
        elif field_path == "biorhythm_type":
            return char.biorhythm_type
        elif field_path == "skills":
            return list(char.skill_ids)
        elif field_path.startswith("stat_adjustments."):
            stat_key = field_path.split(".", 1)[1]
            return char.stat_adjustments.get(stat_key, 0)
        elif field_path.startswith("growth_rates."):
            stat_key = field_path.split(".", 1)[1]
            return char.growth_rates.get(stat_key, 0)
        elif field_path.startswith("laguz_gauge."):
            gauge_key = field_path.split(".", 1)[1]
            return char.laguz_gauge.get(gauge_key, 0)
        return None

    def _store_edit(self, pid: str, field_path: str, value):
        """Store an edit in project.character_edits."""
        edits = self.project.character_edits
        if pid not in edits:
            edits[pid] = {}

        if field_path in ("level", "authority_stars", "biorhythm_type"):
            edits[pid][field_path] = value
        elif field_path == "skills":
            edits[pid]["skill_ids"] = value
        elif field_path.startswith("stat_adjustments."):
            stat_key = field_path.split(".", 1)[1]
            edits[pid].setdefault("stat_adjustments", {})[stat_key] = value
        elif field_path.startswith("growth_rates."):
            stat_key = field_path.split(".", 1)[1]
            edits[pid].setdefault("growth_rates", {})[stat_key] = value
        elif field_path.startswith("laguz_gauge."):
            gauge_key = field_path.split(".", 1)[1]
            edits[pid].setdefault("laguz_gauge", {})[gauge_key] = value

    def _remove_edit(self, pid: str, field_path: str):
        """Remove an edit from project.character_edits if it matches the original."""
        edits = self.project.character_edits
        if pid not in edits:
            return

        if field_path in ("level", "authority_stars", "biorhythm_type"):
            edits[pid].pop(field_path, None)
        elif field_path == "skills":
            edits[pid].pop("skill_ids", None)
        elif field_path.startswith("stat_adjustments."):
            stat_key = field_path.split(".", 1)[1]
            sub = edits[pid].get("stat_adjustments", {})
            sub.pop(stat_key, None)
            if not sub and "stat_adjustments" in edits[pid]:
                del edits[pid]["stat_adjustments"]
        elif field_path.startswith("growth_rates."):
            stat_key = field_path.split(".", 1)[1]
            sub = edits[pid].get("growth_rates", {})
            sub.pop(stat_key, None)
            if not sub and "growth_rates" in edits[pid]:
                del edits[pid]["growth_rates"]
        elif field_path.startswith("laguz_gauge."):
            gauge_key = field_path.split(".", 1)[1]
            sub = edits[pid].get("laguz_gauge", {})
            sub.pop(gauge_key, None)
            if not sub and "laguz_gauge" in edits[pid]:
                del edits[pid]["laguz_gauge"]

        # Clean up empty entries
        if pid in edits and not edits[pid]:
            del edits[pid]

    def _on_class_max_stats_changed(self, jid: str, stat_name: str, value):
        """Handle a class max stat change from the info editor."""
        if self.class_db is None:
            return
        class_entry = self.class_db.get(jid)
        if class_entry is None:
            return

        original = class_entry.max_stats.get(stat_name, 0)

        if value == original:
            # Remove edit if it matches original
            if jid in self.project.class_max_stat_edits:
                self.project.class_max_stat_edits[jid].pop(stat_name, None)
                if not self.project.class_max_stat_edits[jid]:
                    del self.project.class_max_stat_edits[jid]
        else:
            if jid not in self.project.class_max_stat_edits:
                self.project.class_max_stat_edits[jid] = {}
            self.project.class_max_stat_edits[jid][stat_name] = value

    def _on_reset(self):
        """Reset the current character to original values."""
        if self._current_pid is None:
            return

        # Remove all character edits for this PID
        self.project.character_edits.pop(self._current_pid, None)

        # Reload the character
        char = self.char_db.get(self._current_pid) if self.char_db else None
        if char:
            self._load_character(char)
        self._model.refresh()

    def _update_counter(self):
        """Update the counter label with visible row count."""
        visible = self._proxy.rowCount()
        filter_key = self._filter_combo.currentData() if self._filter_combo.currentIndex() >= 0 else "all"
        filter_text = {
            "allied": "allied characters",
            "all": "characters",
            "laguz": "laguz characters",
            "beorc": "beorc characters",
        }.get(filter_key, "characters")
        self._counter_label.setText(f"{visible} {filter_text}")
