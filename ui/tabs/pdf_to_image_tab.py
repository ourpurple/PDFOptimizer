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
from core.pdf2img import batch_convert_pdf_to_images
from core.worker import ProcessingWorker


class PdfToImageTabWidget(BaseTabWidget):
    def __init__(self, main_window):
        super().__init__(main_window)
        self.start_button.setText(const.PDF_TO_IMAGE_BUTTON_TEXT)

    def _create_table_widget(self):
        """重写基类方法，创建特定于此选项卡的表格"""
        table = super()._create_table_widget()
        table.setColumnCount(len(const.PDF_TO_IMAGE_HEADERS))
        table.setHorizontalHeaderLabels(const.PDF_TO_IMAGE_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        return table

    def _setup_ui(self):
        super()._setup_ui()

        controls_layout = QHBoxLayout()
        # 使用硬编码字符串替代不存在的常量
        image_format_label = QLabel("图片格式:")
        controls_layout.addWidget(image_format_label)
        self.image_format_combo = QComboBox()
        # 使用正确的常量
        self.image_format_combo.addItems(const.PDF_TO_IMAGE_FORMATS)
        controls_layout.addWidget(self.image_format_combo)
        # 使用硬编码字符串替代不存在的常量
        dpi_label = QLabel("DPI:")
        controls_layout.addWidget(dpi_label)
        self.dpi_combo = QComboBox()
        # 使用正确的常量
        self.dpi_combo.addItems(const.PDF_TO_IMAGE_DPIS)
        # 使用合理的默认值替代不存在的常量
        self.dpi_combo.setCurrentText("150")
        controls_layout.addWidget(self.dpi_combo)
        controls_layout.addStretch()

        self.layout().insertLayout(self.layout().count() - 1, controls_layout)
        self.other_controls.extend([self.image_format_combo, self.dpi_combo])

    def _reset_ui(self):
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            self.file_table.setItem(
                row, 1, QTableWidgetItem("排队中...")
            )

    def start_task(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(
                self, "警告", "请先添加需要转换为图片的PDF文件。"
            )
            return
        output_dir = QFileDialog.getExistingDirectory(
            self, "选择图片保存的文件夹"
        )
        if not output_dir:
            return
        self._reset_ui()
        self.task_started.emit()
        files = self.get_file_list()
        image_format = self.image_format_combo.currentText().lower()
        dpi = int(self.dpi_combo.currentText())

        self.worker = ProcessingWorker(batch_convert_pdf_to_images, files, output_dir, image_format, dpi)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.page_progress.connect(self.on_progress_update)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.finished.connect(self.on_all_finished)
        self.worker.error.connect(lambda msg: CustomMessageBox.critical(self, "错误", msg))
        self.worker.start()

        self.main_window.status_label.setText(
            "正在将PDF转换为图片..."
        )

    def on_progress_update(self, file_index, current_page, total_pages):
        if total_pages > 0:
            progress_percentage = int((current_page / total_pages) * 100)
            self.file_table.setItem(
                file_index,
                1,
                QTableWidgetItem(f"转换中... {progress_percentage}%"),
            )

    def on_file_finished(self, row, result):
        if result.get("success"):
            self.file_table.setItem(
                row, 1, QTableWidgetItem("转换成功")
            )
            self.file_table.item(row, 1).setToolTip(result.get("message"))
        else:
            self.file_table.setItem(
                row, 1, QTableWidgetItem("转换失败")
            )
            error_message = result.get("message", "发生未知错误")
            self.file_table.item(row, 1).setToolTip(error_message)
            CustomMessageBox.warning(
                self,
                "转换失败",
                f"文件处理失败。\n{error_message}",
            )

    def on_all_finished(self):
        self.task_finished.emit("所有PDF转图片任务已完成。")
        self.progress_bar.setValue(100)