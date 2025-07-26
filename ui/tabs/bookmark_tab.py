# -*- coding: utf-8 -*-
import json
import os

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHeaderView,
    QTableWidgetItem,
    QHBoxLayout,
    QCheckBox,
)

from core import batch_add_bookmarks_to_pdfs
from core.worker import ProcessingWorker
from ui import constants as const
from ui.custom_dialog import CustomMessageBox, BookmarkEditDialog
from ui.tabs.base_tab import BaseTabWidget
from ui.widgets import create_control_button


class BookmarkTabWidget(BaseTabWidget):
    """书签功能卡"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._common_bookmarks = []
        self._file_bookmarks = {}
        # 使用正确的常量
        self.start_button.setText(const.BOOKMARK_BUTTON_TEXT)

    def _create_table_widget(self):
        table = super()._create_table_widget()
        table.setColumnCount(len(const.BOOKMARK_HEADERS))
        # 使用正确的常量
        table.setHorizontalHeaderLabels(const.BOOKMARK_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        return table

    def _setup_ui(self):
        super()._setup_ui()

        # 书签控制
        mode_layout = QHBoxLayout()
        # 使用正确的常量
        self.use_common_bookmarks_checkbox = QCheckBox(
            const.BOOKMARK_USE_COMMON_CHECKBOX
        )
        self.use_common_bookmarks_checkbox.stateChanged.connect(
            self.update_controls_state
        )
        mode_layout.addWidget(self.use_common_bookmarks_checkbox)
        mode_layout.addStretch()
        self.layout().insertLayout(2, mode_layout)

        bookmark_ctrl_layout = QHBoxLayout()
        # 使用正确的常量
        self.add_new_bookmark_button = create_control_button(
            const.BOOKMARK_ADD_NEW_BUTTON, self._add_new_bookmark_clicked
        )
        self.edit_common_bookmarks_button = create_control_button(
            const.BOOKMARK_EDIT_BUTTON, self._edit_bookmarks_clicked
        )
        self.import_bookmarks_button = create_control_button(
            const.BOOKMARK_IMPORT_BUTTON, self._import_bookmarks_clicked
        )
        self.export_bookmarks_button = create_control_button(
            const.BOOKMARK_EXPORT_BUTTON, self._export_bookmarks_clicked
        )

        bookmark_ctrl_layout.addWidget(self.add_new_bookmark_button)
        bookmark_ctrl_layout.addWidget(self.edit_common_bookmarks_button)
        bookmark_ctrl_layout.addWidget(self.import_bookmarks_button)
        bookmark_ctrl_layout.addWidget(self.export_bookmarks_button)
        bookmark_ctrl_layout.addStretch()
        self.layout().insertLayout(3, bookmark_ctrl_layout)

        # 将一些控件设为属性，以便在 _update_controls_state 中访问
        self.other_controls = [
            self.use_common_bookmarks_checkbox,
            self.add_new_bookmark_button,
            self.edit_common_bookmarks_button,
            self.import_bookmarks_button,
            self.export_bookmarks_button,
        ]

    def add_files(self, files):
        current_row = self.file_table.rowCount()
        for i, file_path in enumerate(files):
            row = current_row + i
            self.file_table.insertRow(row)
            item_name = QTableWidgetItem(os.path.basename(file_path))
            item_name.setData(Qt.UserRole, file_path)
            self.file_table.setItem(row, 0, item_name)
            # 使用硬编码字符串
            self.file_table.setItem(row, 1, QTableWidgetItem("0"))
            self.file_table.setItem(row, 2, QTableWidgetItem("待处理"))
        self.main_window.status_label.setText(
            f"已添加 {len(files)} 个文件。"
        )
        self.update_controls_state()

    def _reset_ui(self):
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            # 使用硬编码字符串
            self.file_table.setItem(row, 2, QTableWidgetItem("排队中..."))


    def start_task(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先添加需要添加书签的PDF文件。")
            return

        file_paths = self.get_file_list()

        output_dir = None
        if file_paths:
            # 默认输出目录为第一个文件的目录
            output_dir = os.path.dirname(file_paths)
            # 检查所有文件是否在同一目录
            if not all(os.path.dirname(p) == output_dir for p in file_paths):
                 output_dir = QFileDialog.getExistingDirectory(
                    self, "选择添加书签后文件的保存文件夹"
                )
                 if not output_dir:
                     return

        use_common = self.use_common_bookmarks_checkbox.isChecked()
        file_bookmarks = {}
        for file_path in file_paths:
            if use_common:
                file_bookmarks[file_path] = self._common_bookmarks
            else:
                file_bookmarks[file_path] = self._file_bookmarks.get(file_path, [])

        if use_common and not self._common_bookmarks:
            CustomMessageBox.warning(self, "警告", "请先编辑通用书签。")
            return
        if not use_common and not any(file_bookmarks.values()):
            CustomMessageBox.warning(self, "警告", "请为至少一个文件编辑书签。")
            return

        self._reset_ui()
        self.task_started.emit()
        self.main_window.status_label.setText("正在批量添加书签...")

        self.worker = ProcessingWorker(
            batch_add_bookmarks_to_pdfs,
            file_bookmarks=file_bookmarks,
            output_dir=output_dir,
            use_common=use_common,
            common_bookmarks=self._common_bookmarks,
        )
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.file_finished.connect(self._on_file_finished)
        self.worker.finished.connect(self._on_all_finished)
        self.worker.start()

    def _on_file_finished(self, row, result):
        if result.get("success"):
            self.file_table.setItem(row, 2, QTableWidgetItem("添加成功"))
            output_path = result.get("output", "")
            if output_path:
                self.file_table.item(row, 2).setToolTip(
                    f"保存至: {output_path}"
                )
        else:
            self.file_table.setItem(row, 2, QTableWidgetItem("添加失败"))
            error_message = result.get("message", "未知错误")
            self.file_table.item(row, 2).setToolTip(error_message)
            CustomMessageBox.warning(
                self,
                "添加失败",
                f"文件处理失败: {os.path.basename(result.get('file', ''))}\n{error_message}",
            )

    def _on_all_finished(self):
        self.progress_bar.setValue(100)
        self.task_finished.emit("书签批量添加完成。")

    def stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.task_finished.emit("书签任务已手动停止。")

    def _edit_bookmarks_clicked(self):
        use_common = self.use_common_bookmarks_checkbox.isChecked()
        if use_common:
            dlg = BookmarkEditDialog(self, bookmarks=self._common_bookmarks)
            if dlg.exec() == QDialog.Accepted:
                self._common_bookmarks = dlg.get_bookmarks()
                self.update_controls_state()
        else:
            selected_items = self.file_table.selectedItems()
            if not selected_items:
                CustomMessageBox.warning(
                    self,
                    "提示",
                    "请先在表格中选择一个文件以编辑其书签。",
                )
                return
            row = self.file_table.row(selected_items)
            file_path = self.file_table.item(row, 0).data(Qt.UserRole)
            bookmarks = self._file_bookmarks.get(file_path, [])
            dlg = BookmarkEditDialog(self, bookmarks=bookmarks)
            if dlg.exec() == QDialog.Accepted:
                self._file_bookmarks[file_path] = dlg.get_bookmarks()
                self.file_table.setItem(
                    row,
                    1,
                    QTableWidgetItem(str(len(self._file_bookmarks[file_path]))),
                )
                self.update_controls_state()

    def _import_bookmarks_clicked(self):
        path, _ = QFileDialog.getOpenFileName(
            self, "导入书签配置", "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            with open(path, "r", encoding="utf-8") as f:
                data = json.load(f)
            if "all" in data:
                self._common_bookmarks = data["all"]
                self.use_common_bookmarks_checkbox.setChecked(True)
            else:
                self._file_bookmarks = data
                self.use_common_bookmarks_checkbox.setChecked(False)

            for row in range(self.file_table.rowCount()):
                file_path = self.file_table.item(row, 0).data(Qt.UserRole)
                if file_path in self._file_bookmarks:
                    self.file_table.setItem(
                        row, 1, QTableWidgetItem(str(len(self._file_bookmarks[file_path])))
                    )
                elif self._common_bookmarks:
                     self.file_table.setItem(
                        row, 1, QTableWidgetItem(str(len(self._common_bookmarks)))
                    )
            self.update_controls_state()
            CustomMessageBox.information(self, "导入成功", "书签配置已成功导入。")

        except Exception as e:
            CustomMessageBox.warning(
                self,
                "导入失败",
                f"无法导入书签配置文件。\n错误: {str(e)}",
            )

    def _export_bookmarks_clicked(self):
        path, _ = QFileDialog.getSaveFileName(
            self, "导出书签配置", "", "JSON files (*.json)"
        )
        if not path:
            return
        try:
            if self.use_common_bookmarks_checkbox.isChecked():
                data = {"all": self._common_bookmarks}
            else:
                data = self._file_bookmarks
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            CustomMessageBox.information(
                self, "导出成功", "书签配置已成功导出。"
            )
        except Exception as e:
            CustomMessageBox.warning(
                self,
                "导出失败",
                f"无法导出书签配置文件。\n错误: {str(e)}",
            )

    def update_controls_state(self):
        super().update_controls_state()
        is_running = self._is_task_running
        files_exist = self.file_table.rowCount() > 0
        use_common = self.use_common_bookmarks_checkbox.isChecked()

        # 根据是否使用通用书签，判断导出按钮是否可用
        can_export = False
        if use_common:
            can_export = bool(self._common_bookmarks)
        elif files_exist:
            # 只要有任何一个文件设置了书签，就允许导出
            can_export = any(self._file_bookmarks.values())

        self.export_bookmarks_button.setEnabled(not is_running and can_export)

    def _add_new_bookmark_clicked(self):
        use_common = self.use_common_bookmarks_checkbox.isChecked()
        if use_common:
            # 对于通用书签，直接打开编辑对话框来添加
            self._edit_bookmarks_clicked()
        else:
            # 对于独立书签，需要先选择文件
            selected_items = self.file_table.selectedItems()
            if not selected_items:
                CustomMessageBox.warning(
                    self, "提示", "请先在表格中选择一个文件以添加书签。"
                )
                return
            # 调用编辑逻辑，因为添加新书签本质上也是编辑
            self._edit_bookmarks_clicked()