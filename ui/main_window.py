import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLabel, QFileDialog, QTableWidget, QProgressBar, QHBoxLayout,
    QComboBox, QHeaderView, QTableWidgetItem, QMessageBox, QAbstractItemView
)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData
from PySide6.QtGui import QIcon
import os
from core.optimizer import (
    optimize_pdf, convert_to_curves_with_ghostscript, is_ghostscript_installed,
    optimize_pdf_with_ghostscript, merge_pdfs, merge_pdfs_with_ghostscript
)

def resource_path(relative_path):
    """ Get absolute path to resource, works for dev and for PyInstaller """
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

class Worker(QThread):
    file_finished = Signal(int, dict)
    total_progress = Signal(int)

    def __init__(self, files, quality_preset, engine):
        super().__init__()
        self.files = files
        self.quality_preset = quality_preset
        self.engine = engine
        self.is_running = True

    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            if not self.is_running:
                break
            
            self.file_finished.emit(i, {"status": "处理中..."})
            
            dir_name = os.path.dirname(file_path)
            base_name = os.path.basename(file_path)
            name, ext = os.path.splitext(base_name)
            if self.engine == "Ghostscript 引擎":
                output_suffix = "_optimized_ghostscript"
            else:
                output_suffix = "_optimized_pikepdf"
            output_path = os.path.join(dir_name, f"{name}{output_suffix}{ext}")

            if self.engine == "Ghostscript 引擎":
                result = optimize_pdf_with_ghostscript(file_path, output_path, self.quality_preset)
            else:
                result = optimize_pdf(file_path, output_path, self.quality_preset)
            self.file_finished.emit(i, result)
            
            self.total_progress.emit(int(((i + 1) / total_files) * 100))

    def stop(self):
        self.is_running = False


class CurvesWorker(QThread):
    file_finished = Signal(int, dict)
    total_progress = Signal(int)

    def __init__(self, files):
        super().__init__()
        self.files = files
        self.is_running = True

    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            if not self.is_running:
                break
            
            self.file_finished.emit(i, {"status": "转曲中 (Ghostscript)..."})
            
            dir_name = os.path.dirname(file_path)
            base_name = os.path.basename(file_path)
            name, ext = os.path.splitext(base_name)
            output_path = os.path.join(dir_name, f"{name}_curved_ghostscript{ext}")

            result = convert_to_curves_with_ghostscript(file_path, output_path)
            self.file_finished.emit(i, result)
            
            self.total_progress.emit(int(((i + 1) / total_files) * 100))

    def stop(self):
        self.is_running = False


class MergeWorker(QThread):
    file_finished = Signal(int, dict)
    total_progress = Signal(int)

    def __init__(self, files, output_dir, engine="pikepdf"):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.engine = engine
        self.is_running = True

    def run(self):
        output_path = os.path.join(self.output_dir, "merged_output.pdf")
        if self.engine == "Ghostscript 引擎":
            result = merge_pdfs_with_ghostscript(self.files, output_path, progress_callback=self._update_progress)
        else:
            result = merge_pdfs(self.files, output_path, progress_callback=self._update_progress)
        
        if result["success"]:
            self.total_progress.emit(100)
        
        self.file_finished.emit(0, result)

    def _update_progress(self, value):
        self.total_progress.emit(value)

    def stop(self):
        self.is_running = False


class SortableTableWidget(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setDragDropMode(QAbstractItemView.InternalMove)
        self.setDragEnabled(True)
        self.setAcceptDrops(True)
        self.setDropIndicatorShown(True)
        self.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.setSelectionMode(QAbstractItemView.SingleSelection)
        self.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)

    def dropEvent(self, event):
        if event.source() == self and (event.dropAction() == Qt.DropAction.MoveAction or self.dragDropMode() == QAbstractItemView.InternalMove):
            selected_indexes = self.selectedIndexes()
            if not selected_indexes:
                event.ignore()
                return

            source_row = selected_indexes.row()
            
            drop_indicator_position = self.dropIndicatorPosition()
            if drop_indicator_position == QAbstractItemView.DropIndicatorPosition.OnItem:
                drop_row = self.indexAt(event.pos()).row()
            elif drop_indicator_position == QAbstractItemView.DropIndicatorPosition.AboveItem:
                drop_row = self.indexAt(event.pos()).row()
            elif drop_indicator_position == QAbstractItemView.DropIndicatorPosition.BelowItem:
                drop_row = self.indexAt(event.pos()).row() + 1
            else:
                drop_row = self.rowCount()

            if drop_row < 0:
                drop_row = 0
            if drop_row > self.rowCount():
                drop_row = self.rowCount()

            if source_row < drop_row:
                drop_row -= 1

            row_data = []
            for col in range(self.columnCount()):
                item = self.item(source_row, col)
                if item:
                    new_item = QTableWidgetItem(item.text())
                    new_item.setData(Qt.ItemDataRole.UserRole, item.data(Qt.ItemDataRole.UserRole))
                    new_item.setTextAlignment(item.textAlignment())
                    new_item.setFlags(item.flags())
                    row_data.append(new_item)
                else:
                    row_data.append(None)

            self.removeRow(source_row)
            self.insertRow(drop_row)

            for col, item_data in enumerate(row_data):
                if item_data:
                    self.setItem(drop_row, col, item_data)
            
            event.acceptProposedAction()
            self.viewport().update()
            self.clearSelection()
        else:
            super().dropEvent(event)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_version = "v2.0.0"
        self.setWindowTitle(f"PDF Optimizer - {self.app_version}")
        self.setGeometry(100, 100, 1200, 750)

        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        main_layout = QVBoxLayout()
        top_controls_layout = QHBoxLayout()
        
        self.quality_label = QLabel("优化质量:")
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["低质量 (最大压缩)", "中等质量 (推荐)", "高质量 (轻度优化)"])
        self.quality_combo.setCurrentIndex(2)
        
        self.engine_label = QLabel("  引擎选择:")
        self.engine_combo = QComboBox()
        self.engine_combo.addItems(["标准引擎 (Pikepdf)"])
        
        top_controls_layout.addWidget(self.quality_label)
        top_controls_layout.addWidget(self.quality_combo)
        top_controls_layout.addWidget(self.engine_label)
        top_controls_layout.addWidget(self.engine_combo)
        top_controls_layout.addStretch()

        self.select_button = QPushButton("选择 PDF 文件")
        self.select_button.clicked.connect(self.select_files)
        top_controls_layout.addWidget(self.select_button)

        self.clear_button = QPushButton("清除列表")
        self.clear_button.clicked.connect(self.clear_list)
        top_controls_layout.addWidget(self.clear_button)

        main_layout.addLayout(top_controls_layout)

        self.file_table = SortableTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["文件", "原始大小", "优化后大小", "压缩率", "状态"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeMode.Stretch)
        main_layout.addWidget(self.file_table)

        buttons_layout = QHBoxLayout()
        self.optimize_button = QPushButton("开始优化")
        self.optimize_button.clicked.connect(self.start_optimization)
        buttons_layout.addWidget(self.optimize_button)

        self.curves_button = QPushButton("开始转曲 (Ghostscript)")
        self.curves_button.clicked.connect(self.start_conversion_to_curves)
        buttons_layout.addWidget(self.curves_button)
        
        self.merge_button = QPushButton("合并 PDF")
        self.merge_button.clicked.connect(self.start_merge_pdfs)
        buttons_layout.addWidget(self.merge_button)

        main_layout.addLayout(buttons_layout)

        self.progress_bar = QProgressBar()
        self.progress_bar.setValue(0)
        main_layout.addWidget(self.progress_bar)
        
        status_layout = QHBoxLayout()
        self.status_label = QLabel("请先选择文件...")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()
        
        self.gs_status_label = QLabel()
        status_layout.addWidget(self.gs_status_label)
        status_layout.addSpacing(20)

        self.about_button = QPushButton("关于")
        self.about_button.clicked.connect(self.show_about_dialog)
        status_layout.addWidget(self.about_button)
        main_layout.addLayout(status_layout)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        self.apply_stylesheet()
        self.check_ghostscript()
        self._update_controls_state()

        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def select_files(self):
        files, _ = QFileDialog.getOpenFileNames(self, "选择 PDF 文件", "", "PDF Files (*.pdf)")
        if files:
            self.file_table.setRowCount(len(files))
            for row, file_path in enumerate(files):
                self.file_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
                self.file_table.setItem(row, 1, QTableWidgetItem("-"))
                self.file_table.setItem(row, 2, QTableWidgetItem("-"))
                self.file_table.setItem(row, 3, QTableWidgetItem("-"))
                self.file_table.setItem(row, 4, QTableWidgetItem("等待中..."))
                self.file_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)

            self.status_label.setText(f"已选择 {len(files)} 个文件。")
            self._update_controls_state()

    def _reset_task_ui(self):
        """Resets the progress bar and file status in the table before a new task."""
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            self.file_table.setItem(row, 2, QTableWidgetItem("-"))
            self.file_table.setItem(row, 3, QTableWidgetItem("-"))
            self.file_table.setItem(row, 4, QTableWidgetItem("排队中..."))

    def _update_controls_state(self, is_task_running=False):
        """
        Updates the enabled/disabled state of UI controls based on app state.
        :param is_task_running: True if a background task is active, False otherwise.
        """
        enable_if_files_exist = not is_task_running and self.file_table.rowCount() > 0
        enable_when_not_running = not is_task_running

        self.optimize_button.setEnabled(enable_if_files_exist)
        self.curves_button.setEnabled(enable_if_files_exist and self.gs_installed)
        self.merge_button.setEnabled(enable_if_files_exist)
        self.clear_button.setEnabled(enable_if_files_exist)
        
        self.select_button.setEnabled(enable_when_not_running)
        
        self.quality_combo.setEnabled(enable_when_not_running)
        self.engine_combo.setEnabled(enable_when_not_running)

    def start_optimization(self):
        self._reset_task_ui()
        self._update_controls_state(is_task_running=True)
        
        files = [self.file_table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.file_table.rowCount())]
        quality = self.quality_combo.currentText()
        engine = self.engine_combo.currentText()

        self.worker = Worker(files, quality, engine)
        self.worker.total_progress.connect(self.update_progress)
        self.worker.file_finished.connect(self.on_file_finished)
        self.worker.finished.connect(self.on_all_finished)
        self.worker.start()
        self.status_label.setText(f"正在使用 {engine} 进行优化...")

    def start_conversion_to_curves(self):
        self._reset_task_ui()
        self._update_controls_state(is_task_running=True)

        files = [self.file_table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.file_table.rowCount())]

        self.curves_worker = CurvesWorker(files)
        self.curves_worker.total_progress.connect(self.update_progress)
        self.curves_worker.file_finished.connect(self.on_file_finished)
        self.curves_worker.finished.connect(self.on_all_finished)
        self.curves_worker.start()
        self.status_label.setText("正在转曲 (使用 Ghostscript)...")

    def update_progress(self, value):
        self.progress_bar.setValue(value)

    def on_file_finished(self, row, result):
        if not result.get("success"):
            print(f"优化失败: {result.get('message')}")
        if result.get("success"):
            orig_size_mb = result.get('original_size', 0) / (1024 * 1024)
            opt_size_mb = result.get('optimized_size', 0) / (1024 * 1024)
            reduction = ((orig_size_mb - opt_size_mb) / orig_size_mb) * 100 if orig_size_mb > 0 else 0
            
            self.file_table.setItem(row, 1, QTableWidgetItem(f"{orig_size_mb:.2f} MB"))
            self.file_table.setItem(row, 2, QTableWidgetItem(f"{opt_size_mb:.2f} MB"))
            self.file_table.setItem(row, 3, QTableWidgetItem(f"{reduction:.1f}%"))
            self.file_table.setItem(row, 4, QTableWidgetItem("成功"))
        else:
            status = result.get("status", "失败")
            error_message = result.get('message', '未知错误')
            self.file_table.setItem(row, 4, QTableWidgetItem(f"{status}: {error_message}"))
            self.file_table.item(row, 4).setToolTip(error_message)

    def on_all_finished(self):
        self.status_label.setText("所有任务已完成！")
        self.progress_bar.setValue(100)
        self._update_controls_state()

    def clear_list(self):
        """Clears the file list and resets the UI to its initial state."""
        self.file_table.setRowCount(0)
        self.status_label.setText("请先选择文件...")
        self.progress_bar.setValue(0)
        self._update_controls_state()

    def show_about_dialog(self):
        """Shows the about dialog using QMessageBox."""
        about_text = f"""
<div style='color:#333333;'>
    <p style='font-size:12pt; font-weight:bold;'>PDF Optimizer</p>
    <p style='font-size:9pt;'>一个用于优化、转曲和处理PDF文件的桌面工具。</p>
    <hr>
    <p style='font-size:9pt;'><b>版本:</b> {self.app_version}</p>
    <p style='font-size:9pt;'><b>作者:</b> WanderInDoor</p>
    <p style='font-size:9pt;'><b>联系方式:</b> 76757488@qq.com</p>
    <p style='font-size:9pt;'><b>源代码:</b> <a href="https://github.com/ourpurple/PDFOptimizer">https://github.com/ourpurple/PDFOptimizer</a></p>
    <hr>
    <p style='font-size:8pt; color:grey;'>基于 PySide6, Pikepdf 和 Ghostscript 构建。</p>
</div>
"""
        QMessageBox.about(self, "关于 PDF Optimizer", about_text)

    def apply_stylesheet(self):
        try:
            # 首先，尝试保留 'ui' 目录的路径，这在开发和结构化构建中很常见。
            stylesheet_path = resource_path("ui/style.qss")
            
            # 如果找不到，则回退到检查包的根目录。
            # 这可以处理资源被平铺打包的情况。
            if not os.path.exists(stylesheet_path):
                stylesheet_path = resource_path("style.qss")

            with open(stylesheet_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())
        except FileNotFoundError:
            print("在预期位置未找到样式表 (style.qss)。将使用默认样式。")

    def check_ghostscript(self):
        self.gs_installed = is_ghostscript_installed()
        if self.gs_installed:
            self.gs_status_label.setText("✅ Ghostscript 已安装")
            self.gs_status_label.setStyleSheet("color: green;")
            self.engine_combo.addItem("Ghostscript 引擎")
            self.engine_combo.setCurrentText("Ghostscript 引擎")
        else:
            self.gs_status_label.setText("❌ 未找到 Ghostscript (转曲和GS优化不可用)")
            self.gs_status_label.setStyleSheet("color: red;")

    def start_merge_pdfs(self):
        output_dir = QFileDialog.getExistingDirectory(self, "选择保存合并后文件的目录")
        if not output_dir:
            self.status_label.setText("合并操作已取消：未选择输出目录。")
            return

        self._reset_task_ui()
        self._update_controls_state(is_task_running=True)

        files_to_merge = [self.file_table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.file_table.rowCount())]
        
        selected_engine = self.engine_combo.currentText()
        
        if not files_to_merge:
            self.status_label.setText("没有文件可供合并。请先选择PDF文件。")
            self.on_all_finished()
            return
            
        self.merge_worker = MergeWorker(files_to_merge, output_dir, engine=selected_engine)
        self.merge_worker.total_progress.connect(self.update_progress)
        self.merge_worker.file_finished.connect(self.on_merge_finished)
        self.merge_worker.finished.connect(self.on_all_finished)
        self.status_label.setText(f"正在使用 {selected_engine} 合并PDF文件...")
        self.merge_worker.start()
        
    def on_merge_finished(self, row_index, result):
        if result.get("success"):
            output_path = result.get('output_path', '未知路径')
            self.status_label.setText(f"PDF 合并成功！文件保存至: {output_path}")
            self.clear_list()
        else:
            self.status_label.setText(f"PDF 合并失败: {result.get('message', '未知错误')}")
            self.on_all_finished()
