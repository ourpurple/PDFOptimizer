# -*- coding: utf-8 -*-
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QProgressBar,
    QTableWidgetItem,
    QHeaderView,
)

from ui import constants as const
from ui.tabs.base_tab import BaseTabWidget
from ui.custom_dialog import CustomMessageBox
from core.converter import batch_convert_to_curves
from core.worker import ProcessingWorker


class CurvesTabWidget(BaseTabWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.gs_installed = False
        self.start_button.setText(const.CURVES_BUTTON_TEXT)

    def _create_table_widget(self):
        """重写基类方法，创建特定于此选项卡的表格"""
        table = super()._create_table_widget()
        table.setColumnCount(3)
        table.setHorizontalHeaderLabels(const.CURVES_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 3):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        return table
        
    def add_files(self, files):
        if not self.gs_installed:
            CustomMessageBox.warning(self, const.ERROR_TITLE, const.ERROR_GS_NOT_FOUND_CURVES)
            return
        current_row = self.file_table.rowCount()
        for i, file_path in enumerate(files):
            row = current_row + i
            size = os.path.getsize(file_path) / (1024 * 1024)
            self.file_table.insertRow(row)
            item_name = QTableWidgetItem(os.path.basename(file_path))
            item_name.setData(Qt.UserRole, file_path)
            self.file_table.setItem(row, 0, item_name)
            self.file_table.setItem(row, 1, QTableWidgetItem(f"{size:.2f} MB"))
            self.file_table.setItem(row, 2, QTableWidgetItem(const.TABLE_STATUS_WAITING))
        
        self.main_window.status_label.setText(const.STATUS_LABEL_FILES_ADDED.format(count=len(files)))
        self.update_controls_state()
    
    def _reset_ui(self):
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            self.file_table.setItem(row, 2, QTableWidgetItem(const.TABLE_STATUS_QUEUED))
            
    def start_task(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(self, const.WARNING_TITLE, const.WARNING_CURVES_NO_FILES)
            return
        self._reset_ui()
        self.task_started.emit()
        files = self.get_file_list()

        self.worker = ProcessingWorker(batch_convert_to_curves, files)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.finished.connect(self.on_all_finished)
        self.worker.error.connect(lambda msg: CustomMessageBox.critical(self, const.ERROR_TITLE, msg))
        self.worker.start()
        
        self.main_window.status_label.setText(const.STATUS_LABEL_CURVING)
        
    def on_file_finished(self, row, result):
        if result.get("success"):
            orig_size = result.get("original_size", 0) / (1024 * 1024)
            self.file_table.setItem(row, 1, QTableWidgetItem(f"{orig_size:.2f} MB"))
            self.file_table.setItem(row, 2, QTableWidgetItem(const.CURVES_SUCCESS))
        else:
            self.file_table.setItem(row, 1, QTableWidgetItem(const.NOT_APPLICABLE))
            self.file_table.setItem(row, 2, QTableWidgetItem(const.CURVES_FAILED))
            error_message = result.get("message", const.UNKNOWN_ERROR)
            self.file_table.item(row, 2).setToolTip(error_message)
            CustomMessageBox.warning(self, const.CURVES_FAILED, f"{const.FILE_PROCESSING_FAILED}\n{error_message}")
            
    def on_all_finished(self):
        self.task_finished.emit(const.CURVES_ALL_FINISHED)
        self.progress_bar.setValue(100)

    def update_controls_state(self):
        super().update_controls_state()
        # 如果 Ghostscript 未安装，则禁用开始按钮
        if not self.gs_installed:
            self.start_button.setEnabled(False)

    def update_gs_status(self, installed):
        self.gs_installed = installed
        self.update_controls_state()