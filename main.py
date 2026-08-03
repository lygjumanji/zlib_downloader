# coding:utf-8
import sys
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt
from app.utils.log import setup_logger
from app.views.main_window import Window

if __name__ == "__main__":
    setup_logger()
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    w = Window()
    w.show()
    sys.exit(app.exec())
