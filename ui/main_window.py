import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLabel, QFileDialog, QTableWidget, QProgressBar, QHBoxLayout,
    QComboBox, QHeaderView, QTableWidgetItem, QMessageBox, QAbstractItemView,
    QTabWidget, QMenu
)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData, QUrl
from PySide6.QtGui import QIcon, QDesktopServices
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

    def dropEvent(self, event: 'QDropEvent'):
        if not event.isAccepted() and event.source() == self:
            drop_row = self.drop_on_row(event)
            rows = sorted(list(set(item.row() for item in self.selectedItems())))
            rows_to_move = []
            for row in rows:
                row_data = []
                for column in range(self.columnCount()):
                    item = self.item(row, column)
                    if item:
                        # Clone the item to avoid moving the same item instance
                        clone_item = QTableWidgetItem(item)
                        # Copy user data if it exists
                        for role in range(Qt.ItemDataRole.UserRole, Qt.ItemDataRole.UserRole + 100):
                            data = item.data(role)
                            if data is not None:
                                clone_item.setData(role, data)
                        row_data.append(clone_item)
                    else:
                        row_data.append(None)
                rows_to_move.append(row_data)

            # Adjust drop_row for items moved from above
            for row in reversed(rows):
                self.removeRow(row)
                if row < drop_row:
                    drop_row -= 1
            
            # Insert rows at the new position
            for row_index, row_data in enumerate(rows_to_move):
                row = drop_row + row_index
                self.insertRow(row)
                for column, item in enumerate(row_data):
                    if item:
                        self.setItem(row, column, item)

            # Reselect the moved rows
            self.clearSelection()
            for row_index in range(len(rows_to_move)):
                self.selectRow(drop_row + row_index)
            
            event.accept()
        super().dropEvent(event)

    def drop_on_row(self, event):
        index = self.indexAt(event.pos())
        if not index.isValid():
            return self.rowCount()
        return index.row() + 1 if self.is_below(event.pos(), index) else index.row()

    def is_below(self, pos, index):
        rect = self.visualRect(index)
        margin = 2
        if pos.y() - rect.top() < margin:
            return False
        elif rect.bottom() - pos.y() < margin:
            return True
        # Check if the drop position is in the lower half of the row
        return pos.y() - rect.top() > rect.height() / 2

    def keyPressEvent(self, event):
        """处理按键事件"""
        if event.key() == Qt.Key.Key_Delete:
            self.delete_selected_rows()
        super().keyPressEvent(event)
        event.accept()

    def open_selected_file_location(self):
        """打开选中文件所在文件夹"""
        selected_items = self.selectedItems()
        if not selected_items:
            return

        row = selected_items[0].row()
        item = self.item(row, 0)
        if item:
            file_path = item.data(Qt.ItemDataRole.UserRole)
            if file_path and os.path.exists(os.path.dirname(file_path)):
                folder = os.path.dirname(file_path)
                QDesktopServices.openUrl(QUrl.fromLocalFile(folder))

    def contextMenuEvent(self, event):
        """创建右键菜单"""
        if not self.selectedItems():
            return

        menu = QMenu(self)
        open_folder_action = menu.addAction("打开所在文件夹")
        menu.addSeparator()
        move_up_action = menu.addAction("上移")
        move_down_action = menu.addAction("下移")
        delete_action = menu.addAction("删除")

        action = menu.exec(self.mapToGlobal(event.pos()))

        if action == open_folder_action:
            self.open_selected_file_location()
        elif action == move_up_action:
            self.move_row_up()
        elif action == move_down_action:
            self.move_row_down()
        elif action == delete_action:
            self.delete_selected_rows()

    def move_row_up(self):
        """向上移动选定的行"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows or selected_rows == 0:
            return

        for row in selected_rows:
            self.move_row(row, row - 1)
        
        self.clearSelection()
        for row in selected_rows:
            self.selectRow(row - 1)

    def move_row_down(self):
        """向下移动选定的行"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())), reverse=True)
        if not selected_rows or selected_rows >= self.rowCount() - 1:
            return

        for row in selected_rows:
            self.move_row(row, row + 1)

        self.clearSelection()
        for row in selected_rows:
            self.selectRow(row + 1)
    
    def move_row(self, source_row, dest_row):
        """移动一行"""
        if source_row == dest_row or dest_row < 0 or dest_row >= self.rowCount():
            return
            
        row_data = []
        for col in range(self.columnCount()):
            item = self.takeItem(source_row, col)
            row_data.append(item)

        self.removeRow(source_row)
        self.insertRow(dest_row)

        for col, item in enumerate(row_data):
            self.setItem(dest_row, col, item)

    def delete_selected_rows(self):
        """删除所有选定的行"""
        selected_rows = set()
        for item in self.selectedItems():
            selected_rows.add(item.row())

        for row in sorted(list(selected_rows), reverse=True):
            self.removeRow(row)

def resource_path(relative_path):
    """获取资源的绝对路径"""
    if hasattr(sys, '_MEIPASS'):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)

class BaseWorker(QThread):
    """基础工作线程类"""
    total_progress = Signal(int)
    file_finished = Signal(int, dict)

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
                filename, ext = os.path.splitext(os.path.basename(file_path))
                engine_name = self.engine.replace(" 引擎", "")
                new_filename = f"{filename}[{engine_name}][已优化]{ext}"
                output_path = os.path.join(os.path.dirname(file_path), new_filename)
                
                if "Ghostscript" in self.engine:
                    result = optimize_pdf_with_ghostscript(file_path, output_path, self.quality)
                else:
                    result = optimize_pdf(file_path, output_path, self.quality)

                if result.get("success"):
                    self.file_finished.emit(i, {
                        "success": True,
                        "original_size": result["original_size"],
                        "optimized_size": result["optimized_size"]
                    })
                else:
                    self.file_finished.emit(i, {
                        "success": False,
                        "message": result.get("message", "未知错误")
                    })

            except Exception as e:
                self.file_finished.emit(i, {
                    "success": False,
                    "message": f"文件处理异常: {str(e)}"
                })

            progress = int((i + 1) / total_files * 100)
            self.total_progress.emit(progress)

class MergeWorker(BaseWorker):
    """PDF合并工作线程"""
    def __init__(self, files, output_path, engine):
        super().__init__()
        self.files = files
        self.output_path = output_path
        self.engine = engine

    def run(self):
        try:
            if "Ghostscript" in self.engine:
                result = merge_pdfs_with_ghostscript(self.files, self.output_path)
            else:
                result = merge_pdfs(self.files, self.output_path)

            if result.get("success"):
                self.file_finished.emit(0, {
                    "success": True,
                    "output_path": self.output_path
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
                filename, ext = os.path.splitext(os.path.basename(file_path))
                new_filename = f"{filename}[Ghostscript][已转曲]{ext}"
                output_path = os.path.join(os.path.dirname(file_path), new_filename)
                result = convert_to_curves_with_ghostscript(file_path, output_path)
                if result.get("success"):
                    self.file_finished.emit(i, {
                        "success": True,
                        "original_size": result.get("original_size", 0),
                        "optimized_size": result.get("optimized_size", 0)
                    })
                else:
                    self.file_finished.emit(i, {
                        "success": False,
                        "message": result.get("message", "未知错误")
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
        self.app_version = "v2.4.0"
        self.setWindowTitle(f"PDF Optimizer - {self.app_version}")
        self.setGeometry(100, 100, 1080, 675)

        icon_path = resource_path("app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))

        self.setAcceptDrops(True)

        main_layout = QVBoxLayout()

        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)

        self.optimize_tab = QWidget()
        self.merge_tab = QWidget()
        self.curves_tab = QWidget()

        self._setup_optimize_tab()
        self._setup_merge_tab()
        self._setup_curves_tab()

        self.tab_widget.addTab(self.optimize_tab, "PDF优化")
        self.tab_widget.addTab(self.merge_tab, "PDF合并")
        self.tab_widget.addTab(self.curves_tab, "PDF转曲")

        self._setup_tab_connections()

        main_layout.addWidget(self.tab_widget)

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
        files, _ = QFileDialog.getOpenFileNames(self, "选择PDF文件", "", "PDF Files (*.pdf)")
        if files:
            current_tab = self.tab_widget.currentIndex()
            if current_tab == 0:
                self.add_files_to_optimize(files)
            elif current_tab == 1:
                self.add_files_to_merge(files)
            elif current_tab == 2:
                self.add_files_to_curves(files)

    def _reset_optimize_ui(self):
        self.progress_bar.setValue(0)
        for row in range(self.file_table.rowCount()):
            self.file_table.setItem(row, 2, QTableWidgetItem("-"))
            self.file_table.setItem(row, 3, QTableWidgetItem("-"))
            self.file_table.setItem(row, 4, QTableWidgetItem("排队中..."))
    
    def _reset_curves_ui(self):
        self.curves_progress_bar.setValue(0)
        for row in range(self.curves_table.rowCount()):
            self.curves_table.setItem(row, 2, QTableWidgetItem("排队中..."))

    def _update_controls_state(self, is_task_running=False):
        enable_when_not_running = not is_task_running
        
        optimize_files_exist = self.file_table.rowCount() > 0
        self.optimize_button.setEnabled(enable_when_not_running and optimize_files_exist)
        self.clear_button.setEnabled(enable_when_not_running and optimize_files_exist)
        self.quality_combo.setEnabled(enable_when_not_running)
        self.engine_combo.setEnabled(enable_when_not_running)
        self.stop_button.setEnabled(is_task_running)
        
        merge_files_exist = self.merge_table.rowCount() > 0
        self.merge_button.setEnabled(enable_when_not_running and merge_files_exist)
        self.merge_clear_button.setEnabled(enable_when_not_running and merge_files_exist)
        self.merge_engine_combo.setEnabled(enable_when_not_running)
        self.merge_stop_button.setEnabled(is_task_running)

        curves_files_exist = self.curves_table.rowCount() > 0
        self.curves_button.setEnabled(enable_when_not_running and curves_files_exist and self.gs_installed)
        self.curves_clear_button.setEnabled(enable_when_not_running and curves_files_exist)
        self.curves_stop_button.setEnabled(is_task_running)

        self.select_button.setEnabled(enable_when_not_running)
        self.merge_select_button.setEnabled(enable_when_not_running)
        self.curves_select_button.setEnabled(enable_when_not_running)

    def start_optimization(self):
        if self.file_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请先选择要优化的PDF文件。")
            return

        self._reset_optimize_ui()
        self._update_controls_state(is_task_running=True)

        files = [self.file_table.item(i, 0).data(Qt.ItemDataRole.UserRole) 
                for i in range(self.file_table.rowCount())]

        quality = self.quality_combo.currentText()
        engine = self.engine_combo.currentText()

        self.optimize_worker = OptimizeWorker(files, quality, engine)
        self.optimize_worker.total_progress.connect(self.progress_bar.setValue)
        self.optimize_worker.file_finished.connect(self.on_optimize_file_finished)
        self.optimize_worker.finished.connect(self.on_optimize_all_finished)
        self.optimize_worker.start()

        self.status_label.setText(f"正在使用 {engine} 进行优化...")

    def start_conversion_to_curves(self):
        if self.curves_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "请先选择要转曲的PDF文件。")
            return

        self._reset_curves_ui()
        self._update_controls_state(is_task_running=True)

        files = [self.curves_table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.curves_table.rowCount())]

        self.curves_worker = CurvesWorker(files)
        self.curves_worker.total_progress.connect(self.curves_progress_bar.setValue)
        self.curves_worker.file_finished.connect(self.on_curves_file_finished)
        self.curves_worker.finished.connect(self.on_curves_all_finished)
        self.curves_worker.start()
        self.status_label.setText("正在转曲 (使用 Ghostscript)...")

    def on_optimize_file_finished(self, row, result):
        if result.get("success"):
            orig_size = result["original_size"] / (1024 * 1024)
            opt_size = result["optimized_size"] / (1024 * 1024)
            reduction = ((orig_size - opt_size) / orig_size) * 100 if orig_size > 0 else 0

            self.file_table.setItem(row, 1, QTableWidgetItem(f"{orig_size:.2f} MB"))
            self.file_table.setItem(row, 2, QTableWidgetItem(f"{opt_size:.2f} MB"))
            self.file_table.setItem(row, 3, QTableWidgetItem(f"{reduction:.1f}%"))
            self.file_table.setItem(row, 4, QTableWidgetItem("优化成功"))
        else:
            self.file_table.setItem(row, 4, QTableWidgetItem("优化失败"))
            error_message = result.get("message", "未知错误")
            self.file_table.item(row, 4).setToolTip(error_message)
            QMessageBox.warning(self, "优化失败", f"文件处理失败：\n{error_message}")
            
    def on_curves_file_finished(self, row, result):
        if result.get("success"):
            self.curves_table.setItem(row, 2, QTableWidgetItem("转曲成功"))
        else:
            self.curves_table.setItem(row, 2, QTableWidgetItem("转曲失败"))
            error_message = result.get("message", "未知错误")
            self.curves_table.item(row, 2).setToolTip(error_message)
            QMessageBox.warning(self, "转曲失败", f"文件处理失败：\n{error_message}")

    def on_optimize_all_finished(self):
        self.status_label.setText("PDF优化完成！")
        self.progress_bar.setValue(100)
        self._update_controls_state()

    def on_merge_all_finished(self):
        self.status_label.setText("PDF合并完成！")
        self.merge_progress_bar.setValue(100)
        self._update_controls_state()

    def on_curves_all_finished(self):
        self.status_label.setText("PDF转曲完成！")
        self.curves_progress_bar.setValue(100)
        self._update_controls_state()

    def clear_current_list(self):
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0:
            self.file_table.setRowCount(0)
            self.progress_bar.setValue(0)
            self.status_label.setText("请选择要优化的PDF文件...")
        elif current_tab == 1:
            self.merge_table.setRowCount(0)
            self.merge_progress_bar.setValue(0)
            self.status_label.setText("请选择要合并的PDF文件...")
        elif current_tab == 2:
            self.curves_table.setRowCount(0)
            self.curves_progress_bar.setValue(0)
            self.status_label.setText("请选择要转曲的PDF文件...")
        self._update_controls_state()

    def show_about_dialog(self):
        about_text = f"""
<div style='color:#333333;'>
    <p style='font-size:12pt; font-weight:bold;'>PDF Optimizer</p>
    <p style='font-size:9pt;'>一个用于优化、转曲和处理PDF文件的桌面工具。</p>
    <hr>
    <p style='font-size:9pt;'><b>版        本:</b> {self.app_version}</p>
    <p style='font-size:9pt;'><b>作        者:</b> WanderInDoor</p>
    <p style='font-size:9pt;'><b>联系方式:</b> 76757488@qq.com</p>
    <p style='font-size:9pt;'><b>源   代   码:</b> <a href="https://github.com/ourpurple/PDFOptimizer">https://github.com/ourpurple/PDFOptimizer</a></p>
    <hr>
    <p style='font-size:8pt; color:grey;'>基于 PySide6, Pikepdf 和 Ghostscript 构建。</p>
</div>
"""
        msg_box = QMessageBox(self)
        msg_box.setWindowTitle("关于 PDF Optimizer")
        msg_box.setTextFormat(Qt.TextFormat.RichText)
        msg_box.setText(about_text)
        msg_box.exec()

    def apply_stylesheet(self):
        style_path = resource_path("ui/style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def check_ghostscript(self):
        self.gs_installed = is_ghostscript_installed()
        if self.gs_installed:
            self.gs_status_label.setText("✅ Ghostscript 已安装")
            self.gs_status_label.setStyleSheet("color: green;")
            if self.engine_combo.findText("Ghostscript 引擎") == -1:
                self.engine_combo.addItem("Ghostscript 引擎")
            self.engine_combo.setCurrentText("Ghostscript 引擎")
            if self.merge_engine_combo.findText("Ghostscript 引擎") == -1:
                self.merge_engine_combo.addItem("Ghostscript 引擎")
        else:
            self.gs_status_label.setText("❌ 未找到 Ghostscript (转曲和GS优化不可用)")
            self.gs_status_label.setStyleSheet("color: red;")
            
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
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

        self.status_label.setText(f"已添加 {len(files)} 个文件到优化列表。")
        self._update_controls_state()

    def add_files_to_merge(self, files):
        current_row = self.merge_table.rowCount()
        self.merge_table.setRowCount(current_row + len(files))

        for i, file_path in enumerate(files):
            row = current_row + i
            self.merge_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.merge_table.setItem(row, 1, QTableWidgetItem("等待中..."))
            self.merge_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)

        self.status_label.setText(f"已添加 {len(files)} 个文件到合并列表。")
        self._update_controls_state()

    def add_files_to_curves(self, files):
        if not self.gs_installed:
            QMessageBox.warning(self, "错误", "未检测到Ghostscript，无法使用转曲功能。")
            return

        current_row = self.curves_table.rowCount()
        self.curves_table.setRowCount(current_row + len(files))

        for i, file_path in enumerate(files):
            row = current_row + i
            size = os.path.getsize(file_path) / (1024 * 1024)
            self.curves_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.curves_table.setItem(row, 1, QTableWidgetItem(f"{size:.2f} MB"))
            self.curves_table.setItem(row, 2, QTableWidgetItem("等待中..."))
            self.curves_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)

        self.status_label.setText(f"已添加 {len(files)} 个文件到转曲列表。")
        self._update_controls_state()

    def closeEvent(self, event):
        if hasattr(self, 'optimize_worker') and self.optimize_worker.isRunning():
            self.optimize_worker.stop()
        if hasattr(self, 'merge_worker') and self.merge_worker.isRunning():
            self.merge_worker.stop()
        if hasattr(self, 'curves_worker') and self.curves_worker.isRunning():
            self.curves_worker.stop()
        event.accept()
    
    def stop_current_task(self):
        current_tab = self.tab_widget.currentIndex()
        if current_tab == 0 and hasattr(self, 'optimize_worker') and self.optimize_worker.isRunning():
            self.optimize_worker.stop()
            self.status_label.setText("优化任务已停止")
        elif current_tab == 1 and hasattr(self, 'merge_worker') and self.merge_worker.isRunning():
            self.merge_worker.stop()
            self.status_label.setText("合并任务已停止")
        elif current_tab == 2 and hasattr(self, 'curves_worker') and self.curves_worker.isRunning():
            self.curves_worker.stop()
            self.status_label.setText("转曲任务已停止")
        self._update_controls_state(is_task_running=False)

    def start_merge_pdfs(self):
        if self.merge_table.rowCount() < 2:
            QMessageBox.warning(self, "警告", "请至少选择两个PDF文件进行合并。")
            return

        first_file_item = self.merge_table.item(0, 0)
        suggested_path = ""
        if first_file_item:
            first_file_path = first_file_item.data(Qt.ItemDataRole.UserRole)
            first_file_name, ext = os.path.splitext(os.path.basename(first_file_path))
            num_files = self.merge_table.rowCount()
            suggested_filename = f"{first_file_name}[已合并{num_files}个PDF文件]{ext}"
            output_dir = os.path.dirname(first_file_path)
            suggested_path = os.path.join(output_dir, suggested_filename)

        output_path, _ = QFileDialog.getSaveFileName(
            self, "选择合并后文件的保存位置", suggested_path, "PDF Files (*.pdf)")

        if not output_path:
            return
        
        if not output_path.lower().endswith('.pdf'):
            output_path += '.pdf'

        self.merge_progress_bar.setValue(0)
        self._update_controls_state(is_task_running=True)

        files = [self.merge_table.item(i, 0).data(Qt.ItemDataRole.UserRole) 
                for i in range(self.merge_table.rowCount())]
        
        engine = self.merge_engine_combo.currentText()
        self.merge_worker = MergeWorker(files, output_path, engine)
        self.merge_worker.total_progress.connect(self.merge_progress_bar.setValue)
        self.merge_worker.file_finished.connect(self.on_merge_file_finished)
        self.merge_worker.finished.connect(self.on_merge_all_finished)
        self.merge_worker.start()
        self.status_label.setText("正在合并PDF文件...")
        
    def on_merge_file_finished(self, row, result):
        if result.get("success"):
            for r in range(self.merge_table.rowCount()):
                 self.merge_table.setItem(r, 1, QTableWidgetItem("合并成功"))
            QMessageBox.information(self, "成功", f"文件已成功合并到:\n{result.get('output_path')}")
        else:
            for r in range(self.merge_table.rowCount()):
                self.merge_table.setItem(r, 1, QTableWidgetItem("合并失败"))
            error_message = result.get("message", "未知错误")
            QMessageBox.warning(self, "合并失败", f"合并失败：\n{error_message}")

    def _setup_optimize_tab(self):
        optimize_layout = QVBoxLayout(self.optimize_tab)

        file_select_layout = QHBoxLayout()
        self.select_button = QPushButton("选择PDF文件")
        self.select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.select_button)
        file_select_layout.addStretch()
        optimize_layout.addLayout(file_select_layout)

        self.file_table = SortableTableWidget()
        self.file_table.setColumnCount(5)
        self.file_table.setHorizontalHeaderLabels(["文件名", "原始大小", "优化后大小", "压缩率", "状态"])
        self.file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        optimize_layout.addWidget(self.file_table)

        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        optimize_layout.addWidget(self.progress_bar)

        controls_layout = QHBoxLayout()

        quality_label = QLabel("质量:")
        controls_layout.addWidget(quality_label)
        self.quality_combo = QComboBox()
        self.quality_combo.addItems(["低质量 (最大压缩)", "中等质量 (推荐)", "高质量 (轻度优化)"])
        self.quality_combo.setCurrentText("高质量 (轻度优化)")
        controls_layout.addWidget(self.quality_combo)

        engine_label = QLabel("引擎:")
        controls_layout.addWidget(engine_label)
        self.engine_combo = QComboBox()
        self.engine_combo.addItem("Pikepdf 引擎")
        controls_layout.addWidget(self.engine_combo)
        controls_layout.addStretch()

        self.clear_button = QPushButton("清空列表")
        self.clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.clear_button)

        self.optimize_button = QPushButton("开始优化")
        self.optimize_button.clicked.connect(self.start_optimization)
        controls_layout.addWidget(self.optimize_button)

        self.stop_button = QPushButton("停止")
        self.stop_button.clicked.connect(self.stop_current_task)
        controls_layout.addWidget(self.stop_button)
        
        optimize_layout.addLayout(controls_layout)

    def _setup_merge_tab(self):
        merge_layout = QVBoxLayout(self.merge_tab)

        file_select_layout = QHBoxLayout()
        self.merge_select_button = QPushButton("选择PDF文件")
        self.merge_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.merge_select_button)
        file_select_layout.addStretch()
        merge_layout.addLayout(file_select_layout)

        self.merge_table = SortableTableWidget()
        self.merge_table.setColumnCount(2)
        self.merge_table.setHorizontalHeaderLabels(["文件名", "状态"])
        self.merge_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.merge_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.merge_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        merge_layout.addWidget(self.merge_table)

        self.merge_progress_bar = QProgressBar()
        self.merge_progress_bar.setAlignment(Qt.AlignCenter)
        merge_layout.addWidget(self.merge_progress_bar)

        controls_layout = QHBoxLayout()
        
        merge_engine_label = QLabel("引擎:")
        controls_layout.addWidget(merge_engine_label)
        self.merge_engine_combo = QComboBox()
        self.merge_engine_combo.addItem("Pikepdf 引擎")
        self.merge_engine_combo.setCurrentText("Pikepdf 引擎")
        controls_layout.addWidget(self.merge_engine_combo)

        controls_layout.addStretch()

        self.merge_clear_button = QPushButton("清空列表")
        self.merge_clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.merge_clear_button)

        self.merge_button = QPushButton("开始合并")
        self.merge_button.clicked.connect(self.start_merge_pdfs)
        controls_layout.addWidget(self.merge_button)

        self.merge_stop_button = QPushButton("停止")
        self.merge_stop_button.clicked.connect(self.stop_current_task)
        controls_layout.addWidget(self.merge_stop_button)
        
        merge_layout.addLayout(controls_layout)

    def _setup_curves_tab(self):
        curves_layout = QVBoxLayout(self.curves_tab)

        file_select_layout = QHBoxLayout()
        self.curves_select_button = QPushButton("选择PDF文件")
        self.curves_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.curves_select_button)
        file_select_layout.addStretch()
        curves_layout.addLayout(file_select_layout)

        self.curves_table = SortableTableWidget()
        self.curves_table.setColumnCount(3)
        self.curves_table.setHorizontalHeaderLabels(["文件名", "原始大小", "状态"])
        self.curves_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.curves_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.curves_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        curves_layout.addWidget(self.curves_table)

        self.curves_progress_bar = QProgressBar()
        self.curves_progress_bar.setAlignment(Qt.AlignCenter)
        curves_layout.addWidget(self.curves_progress_bar)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        self.curves_clear_button = QPushButton("清空列表")
        self.curves_clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.curves_clear_button)

        self.curves_button = QPushButton("开始转曲")
        self.curves_button.clicked.connect(self.start_conversion_to_curves)
        controls_layout.addWidget(self.curves_button)

        self.curves_stop_button = QPushButton("停止")
        self.curves_stop_button.clicked.connect(self.stop_current_task)
        controls_layout.addWidget(self.curves_stop_button)
        
        curves_layout.addLayout(controls_layout)

    def _setup_tab_connections(self):
        """设置标签页切换事件连接"""
        self.tab_widget.currentChanged.connect(lambda: self._update_controls_state())