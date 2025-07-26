from PySide6.QtWidgets import QMessageBox, QPushButton
from PySide6.QtGui import QIcon
from PySide6.QtCore import Qt
import os
import sys


def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller"""
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

        self.setStyleSheet(
            """
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
        """
        )

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


from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QLabel,
    QLineEdit,
    QMessageBox,
)
from PySide6.QtCore import Qt


class BookmarkEditDialog(QDialog):
    def __init__(self, parent=None, bookmarks=None, is_new=False):
        super().__init__(parent)
        self.setWindowTitle("编辑书签" if not is_new else "新增书签")
        self.resize(400, 350)
        self.bookmarks = bookmarks or []
        self.is_new = is_new
        self.result_bookmarks = None  # 存储最终的书签结果
        self._setup_ui()
        self._load_bookmarks()

    def _setup_ui(self):
        layout = QVBoxLayout(self)

        # 添加提示标签
        tip_label = QLabel("提示：页码必须为数字，书签内容不能为空")
        tip_label.setStyleSheet("color: #666666; font-size: 10pt;")
        layout.addWidget(tip_label)

        self.table = QTableWidget()
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["页码", "书签内容"])
        self.table.horizontalHeader().setStretchLastSection(True)
        layout.addWidget(self.table)

        btn_layout = QHBoxLayout()
        self.add_btn = QPushButton("添加")
        self.add_btn.clicked.connect(self.add_row)
        btn_layout.addWidget(self.add_btn)
        self.del_btn = QPushButton("删除")
        self.del_btn.clicked.connect(self.delete_row)
        btn_layout.addWidget(self.del_btn)
        btn_layout.addStretch()
        layout.addLayout(btn_layout)

        ok_cancel_layout = QHBoxLayout()
        self.ok_btn = QPushButton("确定")
        self.ok_btn.clicked.connect(self.accept)
        ok_cancel_layout.addWidget(self.ok_btn)
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self.reject)
        ok_cancel_layout.addWidget(self.cancel_btn)
        layout.addLayout(ok_cancel_layout)

    def _load_bookmarks(self):
        self.table.setRowCount(len(self.bookmarks))
        for i, bm in enumerate(self.bookmarks):
            page_item = QTableWidgetItem(str(bm.get("page", "")))
            content_item = QTableWidgetItem(bm.get("title", ""))
            self.table.setItem(i, 0, page_item)
            self.table.setItem(i, 1, content_item)

        # 如果是新增书签模式且没有书签，自动添加一个空行
        if self.is_new and self.table.rowCount() == 0:
            self.add_row()

    def add_row(self):
        row = self.table.rowCount()
        self.table.insertRow(row)
        self.table.setItem(row, 0, QTableWidgetItem(""))
        self.table.setItem(row, 1, QTableWidgetItem(""))

    def delete_row(self):
        selected = self.table.selectedItems()
        if not selected:
            QMessageBox.warning(self, "提示", "请先选中要删除的行！")
            return
        rows = set(item.row() for item in selected)
        for row in sorted(rows, reverse=True):
            self.table.removeRow(row)

    def _validate_and_collect_bookmarks(self):
        """验证并收集书签数据"""
        bookmarks = []
        error_rows = []

        for row in range(self.table.rowCount()):
            page_item = self.table.item(row, 0)
            title_item = self.table.item(row, 1)

            # 跳过完全空白的行
            if (not page_item or not page_item.text().strip()) and (
                not title_item or not title_item.text().strip()
            ):
                continue

            # 验证数据
            try:
                page = int(page_item.text() if page_item else "")
                title = title_item.text().strip() if title_item else ""

                if page <= 0:
                    error_rows.append(row + 1)
                    continue

                if not title:
                    error_rows.append(row + 1)
                    continue

                bookmarks.append({"page": page, "title": title})

            except ValueError:
                error_rows.append(row + 1)

        return bookmarks, error_rows

    def accept(self):
        """验证并保存书签数据"""
        bookmarks, error_rows = self._validate_and_collect_bookmarks()

        if error_rows:
            QMessageBox.warning(
                self,
                "输入错误",
                f"第 {', '.join(map(str, error_rows))} 行的数据无效。\n"
                "请确保：\n"
                "1. 页码为大于0的数字\n"
                "2. 书签内容不能为空",
            )
            return

        if not bookmarks and not self.is_new:
            if (
                QMessageBox.question(
                    self,
                    "确认",
                    "当前没有有效的书签数据，是否继续？",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                )
                != QMessageBox.StandardButton.Yes
            ):
                return

        # 保存验证通过的书签数据
        self.result_bookmarks = bookmarks
        super().accept()

    def get_bookmarks(self):
        """实时返回当前表格中的书签数据"""
        bookmarks, _ = self._validate_and_collect_bookmarks()
        return bookmarks
