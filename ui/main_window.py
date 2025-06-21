import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLabel, QFileDialog, QTableWidget, QProgressBar, QHBoxLayout,
    QComboBox, QHeaderView, QTableWidgetItem, QMessageBox, QAbstractItemView,
    QTabWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData
from PySide6.QtGui import QIcon
import os
from core.optimizer import (
    optimize_pdf, convert_to_curves_with_ghostscript, is_ghostscript_installed,
    optimize_pdf_with_ghostscript, merge_pdfs, merge_pdfs_with_ghostscript
)

class SortableTableWidget(QTableWidget):
    """
    可拖拽排序的表格组件
    """
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setSelectionBehavior(QAbstractItemView.SelectionBehavior.SelectRows)
        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.viewport().setAcceptDrops(True)
        self.setDropIndicatorShown(True)

    def dragEnterEvent(self, event):
        """处理拖拽进入事件"""
        if event.source() == self:
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        """处理拖拽移动事件"""
        if event.source() == self:
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """处理拖拽放下事件"""
        if event.source() == self:
            rows = set()
            for item in self.selectedItems():
                rows.add(item.row())

            target_row = self.rowAt(event.pos().y())
            if target_row == -1:
                target_row = self.rowCount() - 1

            rows = sorted(list(rows))
            if target_row < min(rows):
                # 向上移动
                for row in rows:
                    self._move_row(row, target_row)
                    target_row += 1
            else:
                # 向下移动
                for row in reversed(rows):
                    self._move_row(row, target_row)
                    target_row -= 1

            event.accept()
        else:
            event.ignore()

    def _move_row(self, source_row, target_row):
        """移动表格行"""
        if source_row == target_row:
            return

        # 保存源行的所有列的数据
        row_data = []
        for col in range(self.columnCount()):
            item = self.item(source_row, col)
            if item:
                new_item = QTableWidgetItem(item.text())
                new_item.setData(Qt.ItemDataRole.UserRole, item.data(Qt.ItemDataRole.UserRole))
                row_data.append(new_item)
            else:
                row_data.append(None)

        # 删除源行
        self.removeRow(source_row)

        # 在目标位置插入新行
        self.insertRow(target_row)

        # 填充移动后的行
        for col, item in enumerate(row_data):
            if item:
                self.setItem(target_row, col, item)

    def keyPressEvent(self, event):
        """处理按键事件"""
        if event.key() == Qt.Key.Key_Delete:
            selected_rows = set()
            for item in self.selectedItems():
                selected_rows.add(item.row())

            # 从后向前删除行，以避免索引变化的问题
            for row in sorted(list(selected_rows), reverse=True):
                self.removeRow(row)

            event.accept()
        else:
            super().keyPressEvent(event)
def resource_path(relative_path):
    """获取资源的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class BaseWorker(QThread):
    """基础工作线程类"""
    total_progress = Signal(int)  # 进度信号
    file_finished = Signal(int, dict)  # 文件完成信号

    def __init__(self):
        super().__init__()
        self._is_running = True

    def stop(self):
        """停止工作线程"""
        self._is_running = False

class OptimizeWorker(BaseWorker):
    """PDF优化工作线程"""
    def __init__(self, files, quality, engine):
        super().__init__()
        self.files = files
        self.quality = quality
        self.engine = engine

    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break

            try:
                if "Ghostscript" in self.engine:
                    result = optimize_pdf_with_ghostscript(file_path, self.quality)
                else:
                    result = optimize_pdf(file_path, self.quality)

                self.file_finished.emit(i, {
                    "success": True,
                    "original_size": result["original_size"],
                    "optimized_size": result["optimized_size"]
                })
            except Exception as e:
                self.file_finished.emit(i, {
                    "success": False,
                    "message": str(e)
                })

            progress = int((i + 1) / total_files * 100)
            self.total_progress.emit(progress)

class MergeWorker(BaseWorker):
    """PDF合并工作线程"""
    def __init__(self, files, output_dir):
        super().__init__()
        self.files = files
        self.output_dir = output_dir

    def run(self):
        try:
            # 构建输出文件路径
            output_path = os.path.join(self.output_dir, "merged.pdf")

            # 合并文件
            result = merge_pdfs(self.files, output_path)

            if result.get("success"):
                self.file_finished.emit(0, {
                    "success": True,
                    "output_path": output_path
                })
            else:
                self.file_finished.emit(0, {
                    "success": False,
                    "message": result.get("message", "合并失败")
                })
        except Exception as e:
            self.file_finished.emit(0, {
                "success": False,
                "message": str(e)
            })

        self.total_progress.emit(100)

class CurvesWorker(BaseWorker):
    """PDF转曲工作线程"""
    def __init__(self, files):
        super().__init__()
        self.files = files

    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break

            try:
                result = convert_to_curves_with_ghostscript(file_path)
                self.file_finished.emit(i, {
                    "success": True,
                    "original_size": result.get("original_size", 0),
                    "optimized_size": result.get("optimized_size", 0)
                })
            except Exception as e:
                self.file_finished.emit(i, {
                    "success": False,
                    "message": str(e)
                })

            progress = int((i + 1) / total_files * 100)
            self.total_progress.emit(progress)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_version = "v2.1.0"
        self.setWindowTitle(f"PDF Optimizer - {self.app_version}")
        self.setGeometry(100, 100, 1080, 675)

        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        # 启用文件拖放
        self.setAcceptDrops(True)

        main_layout = QVBoxLayout()

        # 创建标签页控件
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        # 创建三个标签页
        self.optimize_tab = QWidget()
        self.merge_tab = QWidget()
        self.curves_tab = QWidget()

        # 设置标签页布局
        self._setup_optimize_tab()
        self._setup_merge_tab()
        self._setup_curves_tab()

        # 添加标签页
        self.tab_widget.addTab(self.optimize_tab, "PDF优化")
        self.tab_widget.addTab(self.merge_tab, "PDF合并")
        self.tab_widget.addTab(self.curves_tab, "PDF转曲")

        # 设置标签页事件连接
        self._setup_tab_connections()

        main_layout.addWidget(self.tab_widget)

        # 状态栏布局
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

        # 创建中央widget并设置布局
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 应用样式表并检查Ghostscript
        self.apply_stylesheet()
        self.check_ghostscript()
        self._update_controls_state()

        # 设置窗口位置
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def select_files(self):
        """选择文件并添加到当前标签页"""
        files, _ = QFileDialog.getOpenFileNames(self, "选择PDF文件", "", "PDF Files (*.pdf)")
        if files:
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 0:
                self.add_files_to_optimize(files)
            elif current_tab == 1:
                self.add_files_to_merge(files)
            elif current_tab == 2:
                self.add_files_to_curves(files)

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
        """开始PDF优化处理"""
        if self.file_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请先选择要优化的PDF文件。")
            return

        self.progress_bar.setValue(0)
        self._update_controls_state(is_task_running=True)

        files = [self.file_table.item(i, 0).data(Qt.ItemDataRole.UserRole) 
                for i in range(self.file_table.rowCount())]

        quality = self.quality_combo.currentText()
        engine = self.engine_combo.currentText()

        # 使用新的OptimizeWorker
        self.optimize_worker = OptimizeWorker(files, quality, engine)
        self.optimize_worker.total_progress.connect(
            lambda v: self.progress_bar.setValue(v))
        self.optimize_worker.file_finished.connect(self.on_optimize_finished)
        self.optimize_worker.finished.connect(self.on_all_finished)
        self.optimize_worker.start()

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

    def on_optimize_finished(self, row, result):
        """优化完成回调"""
        if result.get("success"):
            orig_size = result["original_size"] / (1024 * 1024)  # 转换为MB
            opt_size = result["optimized_size"] / (1024 * 1024)  # 转换为MB
            reduction = ((orig_size - opt_size) / orig_size) * 100 if orig_size > 0 else 0

            self.file_table.setItem(row, 1, QTableWidgetItem(f"{orig_size:.2f} MB"))
            self.file_table.setItem(row, 2, QTableWidgetItem(f"{opt_size:.2f} MB"))
            self.file_table.setItem(row, 3, QTableWidgetItem(f"{reduction:.1f}%"))
            self.file_table.setItem(row, 4, QTableWidgetItem("优化成功"))
        else:
            self.file_table.setItem(row, 4, QTableWidgetItem("优化失败"))
            error_message = result.get('message', '未知错误')
            self.file_table.item(row, 4).setToolTip(error_message)
            QMessageBox.warning(self, "错误", f"文件处理失败: {error_message}")

    def on_all_finished(self):
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:  # 优化标签页
            self.status_label.setText("PDF优化完成！")
            self.progress_bar.setValue(100)
        elif current_tab == 1:  # 合并标签页
            self.status_label.setText("PDF合并完成！")
            self.merge_progress_bar.setValue(100)
        elif current_tab == 2:  # 转曲标签页
            self.status_label.setText("PDF转曲完成！")
            self.curves_progress_bar.setValue(100)
        self._update_controls_state()

    def clear_current_list(self):
        """清除当前标签页的文件列表"""
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:  # 优化标签页
            self.file_table.setRowCount(0)
            self.progress_bar.setValue(0)
            self.status_label.setText("请选择要优化的PDF文件...")
        elif current_tab == 1:  # 合并标签页
            self.merge_table.setRowCount(0)
            self.merge_progress_bar.setValue(0)
            self.status_label.setText("请选择要合并的PDF文件...")
        elif current_tab == 2:  # 转曲标签页
            self.curves_table.setRowCount(0)
            self.curves_progress_bar.setValue(0)
            self.status_label.setText("请选择要转曲的PDF文件...")
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
        """应用QSS样式表"""
        style_path = resource_path("ui/style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

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
    def dragEnterEvent(self, event):
        """处理文件拖入事件"""
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        """处理文件放下事件"""
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith('.pdf'):
                files.append(file_path)

        if files:
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 0:
                self.add_files_to_optimize(files)
            elif current_tab == 1:
                self.add_files_to_merge(files)
            elif current_tab == 2:
                self.add_files_to_curves(files)

    def add_files_to_optimize(self, files):
        """添加文件到优化列表"""
        current_row = self.file_table.rowCount()
        self.file_table.setRowCount(current_row + len(files))

        for i, file_path in enumerate(files):
            row = current_row + i
            self.file_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.file_table.setItem(row, 1, QTableWidgetItem("-"))
            self.file_table.setItem(row, 2, QTableWidgetItem("-"))
            self.file_table.setItem(row, 3, QTableWidgetItem("-"))
            self.file_table.setItem(row, 4, QTableWidgetItem("等待中..."))
            self.file_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)

        self.status_label.setText(f"已添加 {len(files)} 个文件到优化列表")
        self._update_controls_state()

    def add_files_to_merge(self, files):
        """添加文件到合并列表"""
        current_row = self.merge_table.rowCount()
        self.merge_table.setRowCount(current_row + len(files))

        for i, file_path in enumerate(files):
            row = current_row + i
            self.merge_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.merge_table.setItem(row, 1, QTableWidgetItem("等待中..."))
            self.merge_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)

        self.status_label.setText(f"已添加 {len(files)} 个文件到合并列表")
        self._update_controls_state()

    def add_files_to_curves(self, files):
        """添加文件到转曲列表"""
        if not self.gs_installed:
            QMessageBox.warning(self, "错误", "未检测到Ghostscript，无法使用转曲功能。")
            return

        current_row = self.curves_table.rowCount()
        self.curves_table.setRowCount(current_row + len(files))

        for i, file_path in enumerate(files):
            row = current_row + i
            size = os.path.getsize(file_path) / (1024 * 1024)  # 转换为MB
            self.curves_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.curves_table.setItem(row, 1, QTableWidgetItem(f"{size:.2f} MB"))
            self.curves_table.setItem(row, 2, QTableWidgetItem("等待中..."))
            self.curves_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)

        self.status_label.setText(f"已添加 {len(files)} 个文件到转曲列表")
        self._update_controls_state()

    def closeEvent(self, event):
        """处理窗口关闭事件"""
        if hasattr(self, 'optimize_worker') and self.optimize_worker.isRunning():
            self.optimize_worker.stop()
        if hasattr(self, 'merge_worker') and self.merge_worker.isRunning():
            self.merge_worker.stop()
        if hasattr(self, 'curves_worker') and self.curves_worker.isRunning():
            self.curves_worker.stop()
        event.accept()

    def start_merge_pdfs(self):
        if self.merge_table.rowCount() < 2:
            QMessageBox.warning(self, "警告", "请至少选择两个PDF文件进行合并。")
            return

        self.merge_progress_bar.setValue(0)
        self._update_controls_state(is_task_running=True)

        files = [self.merge_table.item(i, 0).data(Qt.ItemDataRole.UserRole) 
                for i in range(self.merge_table.rowCount())]

        # 选择保存路径
        output_path, _ = QFileDialog.getSaveFileName(
            self, "选择保存位置", "", "PDF Files (*.pdf)")

        if not output_path:
            self._update_controls_state()
            return

        self.merge_worker = MergeWorker(files, os.path.dirname(output_path))
        self.merge_worker.total_progress.connect(
            lambda v: self.merge_progress_bar.setValue(v))
        self.merge_worker.file_finished.connect(self.on_merge_finished)
        self.merge_worker.finished.connect(self.on_all_finished)
        self.merge_worker.start()
        self.status_label.setText("正在合并PDF文件...")
        
    def on_merge_finished(self, row, result):
        if result.get("success"):
            self.merge_table.setItem(row, 1, QTableWidgetItem("合并成功"))
        else:
            self.merge_table.setItem(row, 1, QTableWidgetItem("合并失败"))
            QMessageBox.warning(self, "错误", f"合并失败: {result.get('message', '未知错误')}")

    def _setup_optimize_tab(self):
        """设置PDF优化标签页的UI"""
        optimize_layout = QVBoxLayout(self.optimize_tab)

        # 文件选择区域
        file_select_layout = QHBoxLayout()
        self.select_button = QPushButton("选择PDF文件")
        self.select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.select_button)
        file_select_layout.addStretch()
        optimize_layout.addLayout(file_select_layout)

        # 文件表格
        self.file_table = SortableTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["文件名", "原始大小", "优化后大小", "压缩率", "状态"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        optimize_layout.addWidget(self.file_table)

        # 进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        optimize_layout.addWidget(self.progress_bar)

        # 操作按钮和选项
        controls_layout = QHBoxLayout()

        # 质量选择
        quality_label = QLabel("质量:")
        controls_layout.addWidget(quality_label)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["低", "中", "高", "最高"])
        self.quality_combo.setCurrentText("中")
        controls_layout.addWidget(self.quality_combo)

        # 引擎选择
        engine_label = QLabel("引擎:")
        controls_layout.addWidget(engine_label)
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("Pikepdf 引擎")
        # Ghostscript 引擎会在 check_ghostscript 中动态添加
        controls_layout.addWidget(self.engine_combo)
        controls_layout.addStretch()

        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.clear_button)

        self.optimize_button = QPushButton("开始优化")
        self.optimize_button.clicked.connect(self.start_optimization)
        controls_layout.addWidget(self.optimize_button)
        
        optimize_layout.addLayout(controls_layout)

    def _setup_merge_tab(self):
        """设置PDF合并标签页的UI"""
        merge_layout = QVBoxLayout(self.merge_tab)

        # 文件选择区域
        file_select_layout = QHBoxLayout()
        self.merge_select_button = QPushButton("选择PDF文件")
        self.merge_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.merge_select_button)
        file_select_layout.addStretch()
        merge_layout.addLayout(file_select_layout)

        # 文件表格
        self.merge_table = SortableTableWidget()
        self.merge_table.setColumnCount(2)
        self.merge_table.setHorizontalHeaderLabels(["文件名", "状态"])
        self.merge_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.merge_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.merge_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        merge_layout.addWidget(self.merge_table)

        # 进度条
        self.merge_progress_bar = QProgressBar()
        self.merge_progress_bar.setAlignment(Qt.AlignCenter)
        merge_layout.addWidget(self.merge_progress_bar)

        # 操作按钮
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        self.merge_clear_button = QPushButton("清空列表")
        self.merge_clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.merge_clear_button)

        self.merge_button = QPushButton("开始合并")
        self.merge_button.clicked.connect(self.start_merge_pdfs)
        controls_layout.addWidget(self.merge_button)
        
        merge_layout.addLayout(controls_layout)

    def _setup_curves_tab(self):
        """设置PDF转曲标签页的UI"""
        curves_layout = QVBoxLayout(self.curves_tab)

        # 文件选择区域
        file_select_layout = QHBoxLayout()
        self.curves_select_button = QPushButton("选择PDF文件")
        self.curves_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.curves_select_button)
        file_select_layout.addStretch()
        curves_layout.addLayout(file_select_layout)

        # 文件表格
        self.curves_table = SortableTableWidget()
        self.curves_table.setColumnCount(3)
        self.curves_table.setHorizontalHeaderLabels(["文件名", "原始大小", "状态"])
        self.curves_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.curves_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.curves_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        curves_layout.addWidget(self.curves_table)

        # 进度条
        self.curves_progress_bar = QProgressBar()
        self.curves_progress_bar.setAlignment(Qt.AlignCenter)
        curves_layout.addWidget(self.curves_progress_bar)

        # 操作按钮
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        self.curves_clear_button = QPushButton("清空列表")
        self.curves_clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.curves_clear_button)

        self.curves_button = QPushButton("开始转曲")
        self.curves_button.clicked.connect(self.start_conversion_to_curves)
        controls_layout.addWidget(self.curves_button)
        
        curves_layout.addLayout(controls_layout)

    def _setup_tab_connections(self):
        """设置标签页切换事件连接"""
        self.tab_widget.currentChanged.connect(self._update_controls_state)