"""Skills sub-tab editor for managing a character's equipped skills."""

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QPushButton,
    QTableWidget, QTableWidgetItem, QHeaderView, QGroupBox,
)
from PySide6.QtCore import Signal, Qt

from fe10_mod_editor.models.character_data import CharacterEntry
from fe10_mod_editor.models.class_data import ClassEntry
from fe10_mod_editor.models.skill_data import SkillDatabase, SkillEntry


class CharacterSkillsEditor(QWidget):
    """Editor panel for a character's equipped skills.

    Skills are replacement-only in v1: the number of skill slots is fixed to
    the character's original skill_count. Adding fills empty (None) slots;
    removing sets a slot to None.

    Emits field_changed(pid, "skills", [list_of_sids]) with the full skill list.
    """

    field_changed = Signal(str, str, object)  # (pid, "skills", [sids])

    def __init__(self, parent=None):
        super().__init__(parent)
        self._current_char: CharacterEntry | None = None
        self._current_class: ClassEntry | None = None
        self._skill_db: SkillDatabase | None = None
        self._current_skills: list[str | None] = []  # current skill list (SIDs or None)
        self._max_slots: int = 0
        self._loading = False

        self._build_ui()
        self.setEnabled(False)

    def set_skill_database(self, skill_db: SkillDatabase):
        """Set the SkillDatabase reference used for lookups and the add combo."""
        self._skill_db = skill_db
        self._rebuild_add_combo()

    def _build_ui(self):
        layout = QVBoxLayout(self)

        # ---- Capacity counter ----
        cap_layout = QHBoxLayout()
        self._capacity_label = QLabel("Capacity: 0 / 0 used")
        self._capacity_label.setStyleSheet("font-weight: bold;")
        cap_layout.addWidget(self._capacity_label)
        cap_layout.addStretch()
        layout.addLayout(cap_layout)

        # ---- Skills table ----
        self._skills_table = QTableWidget()
        self._skills_table.setColumnCount(3)
        self._skills_table.setHorizontalHeaderLabels(["Skill Name", "Cost", ""])
        self._skills_table.horizontalHeader().setSectionResizeMode(
            0, QHeaderView.Stretch
        )
        self._skills_table.horizontalHeader().setSectionResizeMode(
            1, QHeaderView.ResizeToContents
        )
        self._skills_table.horizontalHeader().setSectionResizeMode(
            2, QHeaderView.ResizeToContents
        )
        self._skills_table.setSelectionMode(QTableWidget.NoSelection)
        self._skills_table.setEditTriggers(QTableWidget.NoEditTriggers)
        layout.addWidget(self._skills_table)

        # ---- Warning label ----
        self._warning_label = QLabel("")
        self._warning_label.setStyleSheet("color: #cc6600; font-size: 11px;")
        self._warning_label.setWordWrap(True)
        self._warning_label.hide()
        layout.addWidget(self._warning_label)

        # ---- Add skill row ----
        add_group = QGroupBox("Add Skill")
        add_layout = QHBoxLayout(add_group)

        self._add_combo = QComboBox()
        self._add_combo.setEditable(True)
        self._add_combo.setInsertPolicy(QComboBox.NoInsert)
        self._add_combo.setMinimumWidth(180)
        add_layout.addWidget(self._add_combo)

        self._add_btn = QPushButton("Add")
        self._add_btn.clicked.connect(self._on_add_skill)
        add_layout.addWidget(self._add_btn)

        layout.addWidget(add_group)

        layout.addStretch()

    def _rebuild_add_combo(self):
        """Populate the add skill combo box from the skill database."""
        self._add_combo.clear()
        if self._skill_db is None:
            return
        for skill in self._skill_db.all_skills:
            self._add_combo.addItem(skill.display_name, userData=skill.sid)

    def load_character(self, char: CharacterEntry, class_entry: ClassEntry | None,
                       skill_db: SkillDatabase | None, edits: dict):
        """Populate the editor with a character's skill data.

        Args:
            char: The CharacterEntry to display.
            class_entry: The character's ClassEntry (for skill capacity).
            skill_db: The SkillDatabase for lookups.
            edits: The character_edits dict for this PID (may be empty).
        """
        self._loading = True
        self._current_char = char
        self._current_class = class_entry

        if skill_db is not None and skill_db is not self._skill_db:
            self._skill_db = skill_db
            self._rebuild_add_combo()

        self.setEnabled(True)
        self._max_slots = char.skill_count

        # Build the current skill list from edits or original
        if "skill_ids" in edits:
            # Edits store a full replacement list
            self._current_skills = list(edits["skill_ids"])
        else:
            self._current_skills = list(char.skill_ids)

        # Ensure list matches max_slots length
        while len(self._current_skills) < self._max_slots:
            self._current_skills.append(None)
        self._current_skills = self._current_skills[:self._max_slots]

        self._refresh_table()
        self._update_capacity()
        self._update_add_button_state()
        self._check_restrictions()

        self._loading = False

    def _refresh_table(self):
        """Rebuild the skills table from the current skill list."""
        self._skills_table.setRowCount(0)

        active_skills = [(i, sid) for i, sid in enumerate(self._current_skills) if sid]
        self._skills_table.setRowCount(len(active_skills))

        for table_row, (slot_idx, sid) in enumerate(active_skills):
            skill_entry = self._skill_db.get(sid) if self._skill_db else None
            name = skill_entry.display_name if skill_entry else sid
            cost = skill_entry.capacity_cost if skill_entry else 0

            name_item = QTableWidgetItem(name)
            name_item.setData(Qt.UserRole, slot_idx)  # store slot index
            self._skills_table.setItem(table_row, 0, name_item)

            cost_item = QTableWidgetItem(str(cost))
            cost_item.setTextAlignment(Qt.AlignCenter)
            self._skills_table.setItem(table_row, 1, cost_item)

            remove_btn = QPushButton("\u2715")
            remove_btn.setFixedWidth(30)
            remove_btn.clicked.connect(
                lambda checked, si=slot_idx: self._on_remove_skill(si)
            )
            self._skills_table.setCellWidget(table_row, 2, remove_btn)

    def _update_capacity(self):
        """Update the capacity counter label."""
        total_cost = 0
        if self._skill_db:
            for sid in self._current_skills:
                if sid:
                    skill = self._skill_db.get(sid)
                    if skill:
                        total_cost += skill.capacity_cost

        max_cap = self._current_class.skill_capacity if self._current_class else 0
        self._capacity_label.setText(f"Capacity: {total_cost} / {max_cap} used")

        if total_cost > max_cap:
            self._capacity_label.setStyleSheet("font-weight: bold; color: #cc0000;")
        else:
            self._capacity_label.setStyleSheet("font-weight: bold;")

    def _update_add_button_state(self):
        """Disable the add button when all slots are full."""
        filled = sum(1 for s in self._current_skills if s)
        self._add_btn.setEnabled(filled < self._max_slots)

    def _check_restrictions(self):
        """Check skill restrictions and show warnings."""
        if not self._skill_db or not self._current_char:
            self._warning_label.hide()
            return

        jid = self._current_char.jid
        warnings = []
        for sid in self._current_skills:
            if sid:
                reason = self._skill_db.check_restriction(sid, jid)
                if reason:
                    warnings.append(reason)

        if warnings:
            self._warning_label.setText("\n".join(warnings))
            self._warning_label.show()
        else:
            self._warning_label.hide()

    def _emit_skills(self):
        """Emit the full skill list as a field_changed signal."""
        if self._loading or self._current_char is None:
            return
        self.field_changed.emit(
            self._current_char.pid,
            "skills",
            list(self._current_skills),
        )

    def _on_add_skill(self):
        """Add the selected skill to the first empty slot."""
        idx = self._add_combo.currentIndex()
        if idx < 0:
            return

        sid = self._add_combo.currentData()
        if not sid:
            return

        # Find first empty slot
        for i, slot in enumerate(self._current_skills):
            if slot is None:
                self._current_skills[i] = sid
                break
        else:
            return  # no empty slots

        self._refresh_table()
        self._update_capacity()
        self._update_add_button_state()
        self._check_restrictions()
        self._emit_skills()

    def _on_remove_skill(self, slot_idx: int):
        """Remove the skill at the given slot index (set to None)."""
        if 0 <= slot_idx < len(self._current_skills):
            self._current_skills[slot_idx] = None

        self._refresh_table()
        self._update_capacity()
        self._update_add_button_state()
        self._check_restrictions()
        self._emit_skills()
