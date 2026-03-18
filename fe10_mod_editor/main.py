"""Entry point for the FE10 Mod Editor GUI application."""

import sys
from PySide6.QtWidgets import QApplication
from fe10_mod_editor.views.main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
