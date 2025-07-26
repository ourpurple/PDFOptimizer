# -*- coding: utf-8 -*-
import os
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QHBoxLayout,
    QComboBox,
    QLabel,
    QTableWidgetItem,
    QFileDialog,
    QHeaderView,
)

from ui import constants as const
from ui.tabs.base_tab import BaseTabWidget
from ui.custom_dialog import CustomMessageBox
from core.merger import merge_pdfs, merge_pdfs_with_ghostscript
from core.worker import ProcessingWorker


class MergeTabWidget(BaseTabWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.gs_installed = False
        self.start_button.setText(const.MERGE_BUTTON_TEXT)

    def _create_table_widget(self):
        """重写基类方法，创建特定于此选项卡的表格"""
        table = super()._create_table_widget()
        table.setColumnCount(len(const.MERGE_HEADERS))
        table.setHorizontalHeaderLabels(const.MERGE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        return table

    def _setup_ui(self):
        """重写基类方法，添加此选项卡特有的UI控件"""
        super()._setup_ui()

        controls_layout = QHBoxLayout()
        # 使用硬编码字符串替代不存在的常量
        merge_engine_label = QLabel("引擎:")
        controls_layout.addWidget(merge_engine_label)
        self.engine_combo = QComboBox()
        # 使用硬编码字符串替代不存在的常量
        self.engine_combo.addItem("Pikepdf")
        self.engine_combo.setCurrentText("Pikepdf")
        controls_layout.addWidget(self.engine_combo)

        controls_layout.addStretch()

        self.layout().insertLayout(self.layout().count() - 1, controls_layout)
        self.other_controls.append(self.engine_combo)

    def start_task(self):
        if self.file_table.rowCount() < 2:
            CustomMessageBox.warning(
                self, const.WARNING_TITLE, const.WARNING_MERGE_NEED_TWO_FILES
            )
            return

        first_file_item = self.file_table.item(0, 0)
        suggested_path = ""
        if first_file_item:
            first_file_path = first_file_item.data(Qt.UserRole)
            first_file_name, ext = os.path.splitext(os.path.basename(first_file_path))
            num_files = self.file_table.rowCount()
            suggested_filename = (
                f"{first_file_name}[合并_{num_files}个文件]{ext}"
            )
            output_dir = os.path.dirname(first_file_path)
            suggested_path = os.path.join(output_dir, suggested_filename)

        output_path, _ = QFileDialog.getSaveFileName(
            self,
            "选择合并后文件的保存位置",
            suggested_path,
            "PDF Files (*.pdf)",
        )
        if not output_path:
            return

        if not output_path.lower().endswith(".pdf"):
            output_path += ".pdf"

        self.progress_bar.setValue(0)
        self.task_started.emit()

        files = self.get_file_list()
        engine = self.engine_combo.currentText()

        if "Ghostscript" in engine:
            target_function = merge_pdfs_with_ghostscript
        else:
            target_function = merge_pdfs

        self.worker = ProcessingWorker(target_function, files, output_path)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.finished.connect(self.on_all_finished)
        self.worker.error.connect(lambda msg: CustomMessageBox.critical(self, "错误", msg))
        self.worker.start()
        self.main_window.status_label.setText("正在合并PDF...")

    def on_file_finished(self, row, result):
        if result.get("success"):
            for r in range(self.file_table.rowCount()):
                self.file_table.setItem(r, 1, QTableWidgetItem("合并成功"))
            CustomMessageBox.information(
                self,
                "成功",
                f"PDF合并成功！\n文件保存在: {result.get('output_path')}",
            )
        else:
            for r in range(self.file_table.rowCount()):
                self.file_table.setItem(r, 1, QTableWidgetItem("合并失败"))
            error_message = result.get("message", "发生未知错误")
            CustomMessageBox.warning(
                self,
                "合并失败",
                f"处理失败！\n{error_message}",
            )

    def on_all_finished(self):
        self.progress_bar.setValue(100)
        self.task_finished.emit("所有文件合并完成。")

    def update_controls_state(self):
        super().update_controls_state()
        is_running = self._is_task_running
        # Ghostscript 未安装时禁用引擎切换
        self.engine_combo.setEnabled(self.gs_installed and not is_running)

    def update_gs_status(self, installed):
        self.gs_installed = installed
        if installed:
            # 使用硬编码字符串替代不存在的常量
            if self.engine_combo.findText("Ghostscript") == -1:
                self.engine_combo.addItem("Ghostscript")
        else:
            # 使用硬编码字符串替代不存在的常量
            index = self.engine_combo.findText("Ghostscript")
            if index != -1:
                self.engine_combo.removeItem(index)
        self.update_controls_state()