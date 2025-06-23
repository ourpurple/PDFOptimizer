from PySide6.QtWidgets import QMessageBox, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import os

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class CustomMessageBox(QMessageBox):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("提示")
        icon_path = resource_path("ui/app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setStyleSheet("""
            QMessageBox {
                background-color: #FFFAF0; /* FloralWhite */
            }
            QLabel {
                color: #5C4033; /* Dark Brown */
                font-size: 11pt;
            }
            QPushButton {
                background-color: #CD853F; /* Peru */
                color: white;
                border: 1px solid #A0522D; /* Sienna */
                padding: 8px 15px;
                border-radius: 4px;
                min-width: 80px;
            }
            QPushButton:hover {
                background-color: #D2B48C; /* Tan */
            }
            QPushButton:pressed {
                background-color: #A0522D; /* Sienna */
            }
        """)

    @staticmethod
    def information(parent, title, text):
        msg_box = CustomMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Icon.Information)
        msg_box.exec()

    @staticmethod
    def warning(parent, title, text):
        msg_box = CustomMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Icon.Warning)
        msg_box.exec()

    @staticmethod
    def critical(parent, title, text):
        msg_box = CustomMessageBox(parent)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Icon.Critical)
        msg_box.exec()

    @staticmethod
    def about(parent, title, text):
        msg_box = CustomMessageBox(parent)
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setWindowTitle(title)
        msg_box.setText(text)
        msg_box.setIcon(QMessageBox.Icon.NoIcon)
        msg_box.exec()