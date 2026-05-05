import sys
from PyQt6.QtWidgets import QApplication
from gui_components import GameWindow

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = GameWindow()
    window.resize(1290, 600)
    window.show()
    sys.exit(app.exec())