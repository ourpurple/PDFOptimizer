# -*- coding: utf-8 -*-
import os
from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QComboBox,
    QLabel,
    QTableWidgetItem,
    QHeaderView,
)

from ui import constants as const
from ui.tabs.base_tab import BaseTabWidget
from ui.custom_dialog import CustomMessageBox
from core.optimizer import batch_optimize_pdfs
from core.worker import ProcessingWorker


class OptimizeTabWidget(BaseTabWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.gs_installed = False
        self.start_button.setText(const.OPTIMIZE_BUTTON_TEXT)

    def _create_table_widget(self):
        """重写基类方法，创建特定于此选项卡的表格"""
        table = super()._create_table_widget()
        table.setColumnCount(5)
        table.setHorizontalHeaderLabels(const.OPTIMIZE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        for i in range(1, 5):
            table.horizontalHeader().setSectionResizeMode(i, QHeaderView.ResizeToContents)
        return table

    def _setup_ui(self):
        """重写基类方法，添加此选项卡特有的UI控件"""
        super()._setup_ui()

        # 创建一个包含质量和引擎选项的新布局
        controls_layout = QHBoxLayout()
        quality_label = QLabel("质量设置:")
        controls_layout.addWidget(quality_label)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(
            [const.OPTIMIZE_QUALITY_LOW, const.OPTIMIZE_QUALITY_MEDIUM, const.OPTIMIZE_QUALITY_HIGH]
        )
        self.quality_combo.setCurrentText(const.OPTIMIZE_QUALITY_HIGH)
        controls_layout.addWidget(self.quality_combo)

        engine_label = QLabel("优化引擎:")
        controls_layout.addWidget(engine_label)
        self.engine_combo = QComboBox()
        self.engine_combo.addItem(const.OPTIMIZE_ENGINE_PIKEPDF)
        controls_layout.addWidget(self.engine_combo)
        
        controls_layout.addStretch()

        # 将新的控件布局插入到主布局的倒数第二位置（在进度条和按钮之前）
        self.layout().insertLayout(self.layout().count() - 1, controls_layout)
        
        self.other_controls.extend([self.quality_combo, self.engine_combo])


    def add_files(self, files):
        """重写基类方法，以处理此选项卡的特定列"""
        current_row = self.file_table.rowCount()
        for i, file_path in enumerate(files):
            row = current_row + i
            self.file_table.insertRow(row)
            # 文件名
            item_name = QTableWidgetItem(os.path.basename(file_path))
            item_name.setData(Qt.UserRole, file_path)
            self.file_table.setItem(row, 0, item_name)
            # 其他列初始化为等待状态
            for col in range(1, 5):
                 self.file_table.setItem(row, col, QTableWidgetItem("等待中..."))
        
        self.main_window.status_label.setText(
            f"{len(files)} 个文件已添加"
        )
        self.update_controls_state()

    def start_task(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(
                self, "警告", "请先选择要优化的PDF文件。"
            )
            return
        self._reset_ui()
        self.task_started.emit()
        files = self.get_file_list()
        quality = self.quality_combo.currentText()
        engine = self.engine_combo.currentText()
        
        self.worker = ProcessingWorker(batch_optimize_pdfs, files, quality, engine)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.finished.connect(self.on_all_finished)
        self.worker.error.connect(lambda msg: CustomMessageBox.critical(self, "错误", msg))
        self.worker.start()

        self.main_window.status_label.setText(
            f"正在使用 {engine} 引擎进行优化..."
        )

    def _reset_ui(self):
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            for col in range(1, 4):
                self.file_table.setItem(row, col, QTableWidgetItem("等待中..."))
            self.file_table.setItem(row, 4, QTableWidgetItem("排队中"))

    def on_file_finished(self, row, result):
        if result.get("success"):
            orig_size = result["original_size"] / (1024 * 1024)
            opt_size = result["optimized_size"] / (1024 * 1024)
            reduction = (
                ((orig_size - opt_size) / orig_size) * 100 if orig_size > 0 else 0
            )
            self.file_table.setItem(row, 1, QTableWidgetItem(f"{orig_size:.2f} MB"))
            self.file_table.setItem(row, 2, QTableWidgetItem(f"{opt_size:.2f} MB"))
            self.file_table.setItem(row, 3, QTableWidgetItem(f"{reduction:.1f}%"))
            self.file_table.setItem(row, 4, QTableWidgetItem("成功"))
        else:
            self.file_table.setItem(row, 4, QTableWidgetItem("失败"))
            error_message = result.get("message", "未知错误")
            self.file_table.item(row, 4).setToolTip(error_message)
            CustomMessageBox.warning(
                self,
                "优化失败",
                f"文件处理失败:\n{error_message}",
            )

    def on_all_finished(self):
        self.progress_bar.setValue(100)
        self.task_finished.emit("所有文件优化完成！")

    def update_controls_state(self):
        super().update_controls_state()
        is_running = self._is_task_running
        # Ghostscript 未安装时禁用引擎切换
        # Ghostscript 未安装时禁用引擎切换，或者如果安装了但任务正在运行
        self.engine_combo.setEnabled(self.gs_installed and not is_running)


    def update_gs_status(self, installed):
        self.gs_installed = installed
        if installed:
            if self.engine_combo.findText(const.OPTIMIZE_ENGINE_GS) == -1:
                self.engine_combo.addItem(const.OPTIMIZE_ENGINE_GS)
        else:
            # 如果 Ghostscript 不存在，移除该选项
            index = self.engine_combo.findText(const.OPTIMIZE_ENGINE_GS)
            if index != -1:
                self.engine_combo.removeItem(index)
        self.update_controls_state()