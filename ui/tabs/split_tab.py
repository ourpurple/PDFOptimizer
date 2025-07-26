# -*- coding: utf-8 -*-
from PySide6.QtWidgets import (
    QTableWidgetItem,
    QFileDialog,
    QWidget,
    QHeaderView,
)
from PySide6.QtCore import Qt

from ui.custom_dialog import CustomMessageBox
from ui import constants as const
from ui.tabs.base_tab import BaseTabWidget
from core.division import batch_split_pdf
from core.worker import ProcessingWorker
import os


class SplitTabWidget(BaseTabWidget):
    """PDF分割功能卡"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.start_button.setText(const.SPLIT_BUTTON_TEXT)

    def _create_table_widget(self):
        """重写基类方法，创建特定于此选项卡的表格"""
        table = super()._create_table_widget()
        table.setColumnCount(len(const.SPLIT_HEADERS))
        table.setHorizontalHeaderLabels(const.SPLIT_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        return table

    def _reset_ui(self):
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            self.file_table.setItem(row, 1, QTableWidgetItem("排队中..."))

    def start_task(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先添加需要分割的PDF文件。")
            return

        output_dir = QFileDialog.getExistingDirectory(self, "选择分割后文件的保存文件夹")
        if not output_dir:
            return

        self._reset_ui()
        self.task_started.emit()
        self.main_window.status_label.setText("正在分割PDF...")

        files = self.get_file_list()

        self.worker = ProcessingWorker(batch_split_pdf, files, output_dir)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.page_progress.connect(self._on_progress)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.finished.connect(self._on_all_finished)
        self.worker.error.connect(lambda msg: CustomMessageBox.critical(self, "错误", msg))
        self.worker.start()

    def _on_progress(self, file_index, current_page, total_pages):
        if total_pages > 0:
            progress_percentage = int((current_page / total_pages) * 100)
            self.file_table.setItem(
                file_index,
                1,
                QTableWidgetItem(f"分割中... {progress_percentage}%"),
            )

    def _on_file_finished(self, row, result):
        if result.get("success"):
            self.file_table.setItem(row, 1, QTableWidgetItem("分割成功"))
            self.file_table.item(row, 1).setToolTip(result.get("message"))
        else:
            self.file_table.setItem(row, 1, QTableWidgetItem("分割失败"))
            error_message = result.get("message", "发生未知错误")
            self.file_table.item(row, 1).setToolTip(error_message)
            CustomMessageBox.warning(
                self, "分割失败", f"文件处理失败。\n{error_message}"
            )

    def _on_all_finished(self):
        self.progress_bar.setValue(100)
        self.task_finished.emit("所有PDF分割任务已完成。")