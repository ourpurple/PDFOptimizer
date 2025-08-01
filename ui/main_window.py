import sys
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLabel, QFileDialog, QTableWidget, QProgressBar, QHBoxLayout,
    QComboBox, QHeaderView, QTableWidgetItem, QMessageBox, QAbstractItemView,
    QTabWidget, QMenu, QCheckBox, QDialog, QLineEdit, QTextEdit, QFormLayout
)
from PySide6.QtCore import Qt, QThread, Signal, QMimeData, QUrl
from PySide6.QtGui import QDropEvent, QIcon, QDesktopServices
import os
import re
import time
import httpx
import logging
from core import (
    optimize_pdf,
    convert_to_curves_with_ghostscript,
    is_ghostscript_installed,
    is_pandoc_installed,
    convert_markdown_to_docx_with_pandoc,
    preprocess_markdown_for_pandoc,
    optimize_pdf_with_ghostscript,
    merge_pdfs,
    merge_pdfs_with_ghostscript,
    convert_pdf_to_images,
    split_pdf,
    __version__,
    batch_add_bookmarks_to_pdfs
)
from core.ocr import process_images_with_model
from .custom_dialog import CustomMessageBox, BookmarkEditDialog
import json
import dotenv

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

        # 获取选中行的第一列（文件名列）
        row = selected_items[0].row()
        file_path_item = self.item(row, 0)
        if file_path_item:
            file_path = file_path_item.data(Qt.ItemDataRole.UserRole)
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
        move_top_action = menu.addAction("移至顶部")
        move_up_action = menu.addAction("上移")
        move_down_action = menu.addAction("下移")
        move_bottom_action = menu.addAction("移至底部")
        menu.addSeparator()
        delete_action = menu.addAction("删除")

        action = menu.exec(self.mapToGlobal(event.pos()))

        if action == open_folder_action:
            self.open_selected_file_location()
        elif action == move_top_action:
            self.move_to_top()
        elif action == move_up_action:
            self.move_row_up()
        elif action == move_down_action:
            self.move_row_down()
        elif action == move_bottom_action:
            self.move_to_bottom()
        elif action == delete_action:
            self.delete_selected_rows()

    def move_to_top(self):
        """将选中的行移动到顶部"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows:
            return

        # 从上往下移动到顶部
        target_row = 0
        for row in selected_rows:
            # 如果行已经在目标位置之后，需要考虑前面的行移动带来的影响
            actual_row = row + len([r for r in selected_rows if r < row])
            self.move_row(actual_row, target_row)
            target_row += 1

        # 重新选择移动后的行
        self.clearSelection()
        for i in range(len(selected_rows)):
            self.selectRow(i)

    def move_to_bottom(self):
        """将选中的行移动到底部"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows:
            return

        # 计算目标位置（考虑到删除行后总行数的变化）
        total_rows = self.rowCount()
        target_start = total_rows - len(selected_rows)

        # 从下往上移动到底部
        for i, row in enumerate(reversed(selected_rows)):
            target_row = total_rows - i - 1
            # 如果行在目标位置之前，需要考虑前面的行移动带来的影响
            actual_row = row - len([r for r in selected_rows if r > row])
            self.move_row(actual_row, target_row)

        # 重新选择移动后的行
        self.clearSelection()
        for i in range(len(selected_rows)):
            self.selectRow(target_start + i)

    def move_row_up(self):
        """向上移动选定的行"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows or selected_rows == 0:
            return

        for row in selected_rows:
            self.move_row(row, row - 1)
        
        self.clearSelection()
        new_selection = [row - 1 for row in selected_rows]
        for row in new_selection:
            self.selectRow(row)

    def move_row_down(self):
        """向下移动选定的行"""
        selected_rows = sorted(list(set(item.row() for item in self.selectedItems())))
        if not selected_rows:
            return
            
        # 检查最后一个选中的行是否已经是最后一行
        if max(selected_rows) >= self.rowCount() - 1:
            return
            
        # 从下往上移动，避免行号变化影响
        for row in reversed(selected_rows):
            # 移动行
            self.move_row(row, row + 1)

        # 重新选择移动后的行
        self.clearSelection()
        for row in selected_rows:
            if row < self.rowCount() - 1:  # 确保不超出表格范围
                self.selectRow(row + 1)

    def move_row(self, source_row, dest_row):
        """移动一行"""
        if source_row == dest_row or dest_row < 0 or dest_row >= self.rowCount():
            return
            
        # 保存源行的所有列数据
        row_data = []
        for col in range(self.columnCount()):
            item = self.takeItem(source_row, col)
            if item is None:
                item = QTableWidgetItem("")
            row_data.append(item)

        # 删除源行
        self.removeRow(source_row)
        
        # 在目标位置插入新行
        self.insertRow(dest_row)
        
        # 还原数据
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
class PdfToImageWorker(BaseWorker):
    """PDF转图片工作线程"""
    progress_updated = Signal(int, int, int)  # file_index, current_page, total_pages
    def __init__(self, files, output_dir, image_format, dpi):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
        self.image_format = image_format
        self.dpi = dpi
    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break
            try:
                result = convert_pdf_to_images(
                    file_path,
                    self.output_dir,
                    self.image_format,
                    self.dpi,
                    lambda current, total: self.progress_updated.emit(i, current, total)
                )
                
                if result.get("success"):
                    self.file_finished.emit(i, {
                        "success": True,
                        "message": result.get("message", "转换成功")
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
class SplitWorker(BaseWorker):
    """PDF分割工作线程"""
    progress_updated = Signal(int, int, int)
    def __init__(self, files, output_dir):
        super().__init__()
        self.files = files
        self.output_dir = output_dir
    def run(self):
        total_files = len(self.files)
        for i, file_path in enumerate(self.files):
            if not self._is_running:
                break
            try:
                result = split_pdf(
                    file_path,
                    self.output_dir,
                    lambda current, total: self.progress_updated.emit(i, current, total)
                )
                if result.get("success"):
                    self.file_finished.emit(i, {
                        "success": True,
                        "message": result.get("message", "分割成功")
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
class OcrWorker(QThread):
    """PDF OCR 工作线程"""
    ocr_progress = Signal(str)
    ocr_finished = Signal(dict)
    total_progress = Signal(int)
    preview_updated = Signal(str)  # 新增信号，用于更新预览

    def __init__(self, file_path, api_key, model_name, api_base_url, prompt_text, temp_dir, api_provider, temperature=1.0):
        super().__init__()
        self.file_path = file_path
        self.api_key = api_key
        self.model_name = model_name
        self.api_base_url = api_base_url
        self.prompt_text = prompt_text
        self.temp_dir = temp_dir
        self.api_provider = api_provider
        self.temperature = temperature  # 添加温度参数
        self._is_running = True
        self.logger = self._setup_logger()
        self.preview_content = ""  # 用于累积预览内容

    def _setup_logger(self):
        """为当前OCR任务配置独立的日志记录器"""
        log_filename = os.path.splitext(self.file_path)[0] + ".log"
        logger_name = f"OcrLogger_{os.path.basename(self.file_path)}"
        
        logger = logging.getLogger(logger_name)
        
        # 防止重复添加handler
        if not logger.handlers:
            logger.setLevel(logging.INFO)
            handler = logging.FileHandler(log_filename, encoding='utf-8')
            formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)
            
        return logger

    def stop(self):
        self._is_running = False

    def run(self):
        if not self._is_running:
            return

        self.logger.info(f"===== OCR任务开始: {os.path.basename(self.file_path)} =====")
        self.logger.info(f"使用提供商: {self.api_provider}")
        try:
            image_paths = []
            pdf_path = None

            if self.api_provider == "Mistral API":
                # 对于Mistral API，我们直接传递PDF文件路径，不进行图片转换
                self.logger.info("步骤1: Mistral API模式，跳过PDF转图片。")
                self.ocr_progress.emit("Mistral API模式，直接处理PDF...")
                pdf_path = self.file_path
            else:
                # 对于类OpenAI API，需要先将PDF转换为图片
                self.ocr_progress.emit("正在将PDF转换为图片...")
                self.logger.info("步骤1: 开始将PDF转换为图片...")
                file_name_without_ext, _ = os.path.splitext(os.path.basename(self.file_path))
                image_output_dir = os.path.join(self.temp_dir, file_name_without_ext)
                
                if os.path.exists(image_output_dir):
                    import shutil
                    shutil.rmtree(image_output_dir)
                os.makedirs(image_output_dir)
                
                convert_result = convert_pdf_to_images(self.file_path, image_output_dir, dpi=200)
                if not convert_result["success"]:
                    self.logger.error(f"PDF转图片失败: {convert_result['message']}")
                    raise Exception(f"PDF转图片失败: {convert_result['message']}")
                
                self.logger.info("PDF转图片成功。")
                image_paths = sorted(
                    [os.path.join(image_output_dir, f) for f in os.listdir(image_output_dir) if f.lower().endswith('.png')],
                    key=lambda x: int(re.search(r'(\d+)', os.path.basename(x)).group(1)) if re.search(r'(\d+)', os.path.basename(x)) else 0
                )
                
                if not image_paths:
                    self.logger.error("没有从PDF中生成任何图片。")
                    raise Exception("没有从PDF中生成任何图片。")

            # 2. 调用核心OCR处理函数
            def progress_callback(current, total, message, page_content=""):
                if not self._is_running:
                    # 这将中断 process_images_with_model 中的循环
                    return False
                self.ocr_progress.emit(f"AI识别中: {current}/{total}页 - {message}")
                progress = int((current / total) * 100)
                self.total_progress.emit(progress)
                # 更新预览内容 - 只显示当前页内容
                if page_content:
                    # 如果是Mistral API，page_content可能包含所有页面的内容
                    if current == total and total == 1 and "\n\n---\n\n" in page_content:
                        self.preview_content = page_content  # 直接替换
                    else:
                        # 如果是OpenAI兼容API，page_content是单页内容，只显示当前页
                        self.preview_content = page_content
                    self.preview_updated.emit(self.preview_content)
                return True

            self.ocr_progress.emit("正在调用AI模型进行识别...")
            self.logger.info("步骤2: 调用核心OCR模块...")
            
            ocr_result = process_images_with_model(
                image_paths=image_paths,
                pdf_path=pdf_path, # 新增参数
                api_provider=self.api_provider,
                api_key=self.api_key,
                api_base_url=self.api_base_url,
                model_name=self.model_name,
                prompt_text=self.prompt_text,
                logger=self.logger,
                temperature=self.temperature,  # 传递温度参数
                progress_callback=progress_callback
            )

            if not self._is_running:
                raise InterruptedError("OCR task was stopped.")

            # 3. 处理结果
            self.total_progress.emit(100)
            ocr_result['logger'] = self.logger # 确保logger实例被传递回去
            self.ocr_finished.emit(ocr_result)
            
            if ocr_result.get("success"):
                 self.logger.info("===== OCR任务成功结束 =====")
            else:
                 self.logger.warning(f"===== OCR任务结束，但有错误: {ocr_result.get('message')} =====")

        except InterruptedError:
             self.logger.warning("任务已手动停止。")
             self.ocr_finished.emit({"success": False, "message": "任务已手动停止。"})
             self.logger.info("===== OCR任务已停止 =====")
        except NotImplementedError as e:
            self.logger.error(f"OCR功能尚未完全实现: {str(e)}", exc_info=True)
            self.ocr_finished.emit({"success": False, "message": f"功能待定: {str(e)}", "logger": self.logger})
            self.logger.info("===== OCR任务因功能未实现而终止 =====")
        except Exception as e:
            self.logger.error(f"OCR任务发生未知严重错误: {str(e)}", exc_info=True)
            self.ocr_finished.emit({"success": False, "message": str(e), "logger": self.logger})
            self.logger.info("===== OCR任务因错误而终止 =====")
        finally:
            self.total_progress.emit(100)
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_version = f"v{__version__}"
        self.setWindowTitle(f"PDF Optimizer - {self.app_version}")
        self.setGeometry(100, 100, 1080, 720)
        icon_path = resource_path("ui/app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setAcceptDrops(True)
        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.optimize_tab = QWidget()
        self.merge_tab = QWidget()
        self.curves_tab = QWidget()
        self.pdf_to_image_tab = QWidget()
        self.split_tab = QWidget()
        self.bookmark_tab = QWidget()
        self.ocr_tab = QWidget()
        self._setup_optimize_tab()
        self._setup_merge_tab()
        self._setup_curves_tab()
        self._setup_pdf_to_image_tab()
        self._setup_split_tab()
        self._setup_bookmark_tab()
        self._setup_ocr_tab()
        self.tab_widget.addTab(self.optimize_tab, "PDF优化")
        self.tab_widget.addTab(self.merge_tab, "PDF合并")
        self.tab_widget.addTab(self.curves_tab, "PDF转曲")
        self.tab_widget.addTab(self.pdf_to_image_tab, "PDF转图片")
        self.tab_widget.addTab(self.split_tab, "PDF分割")
        self.tab_widget.addTab(self.bookmark_tab, "PDF加书签")
        self.tab_widget.addTab(self.ocr_tab, "PDF OCR")
        self._setup_tab_connections()
        main_layout.addWidget(self.tab_widget)
        status_layout = QHBoxLayout()
        self.status_label = QLabel("请先选择文件...")
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.gs_status_label = QLabel()
        status_layout.addWidget(self.gs_status_label)
        
        self.pandoc_status_label = QLabel()
        status_layout.addWidget(self.pandoc_status_label)

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
        self.check_pandoc()
        self._load_config()
        self._update_controls_state()
        
        self.temp_dir = os.path.join(os.path.expanduser("~"), ".pdfoptimizer", "temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
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
            elif current_tab == 3:
                self.add_files_to_pdf_to_image(files)
            elif current_tab == 4:
                self.add_files_to_split(files)
            elif current_tab == 5: # Bookmark tab
                self.add_files_to_bookmark(files)
            elif current_tab == 6:
                self.add_files_to_ocr(files)
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
    def _reset_pdf_to_image_ui(self):
        self.pdf_to_image_progress_bar.setValue(0)
        for row in range(self.pdf_to_image_table.rowCount()):
            self.pdf_to_image_table.setItem(row, 1, QTableWidgetItem("排队中..."))
    def _reset_split_ui(self):
        self.split_progress_bar.setValue(0)
        for row in range(self.split_table.rowCount()):
            self.split_table.setItem(row, 1, QTableWidgetItem("排队中..."))
    def _reset_bookmark_ui(self):
        self.bookmark_progress_bar.setValue(0)
        for row in range(self.bookmark_file_table.rowCount()):
            self.bookmark_file_table.setItem(row, 1, QTableWidgetItem("排队中..."))
            self.bookmark_file_table.setItem(row, 2, QTableWidgetItem("操作"))
    def _reset_ocr_ui(self):
        self.ocr_progress_bar.setValue(0)
        self.ocr_result_text.clear()
        if self.ocr_table.rowCount() > 0:
            self.ocr_table.setItem(0, 1, QTableWidgetItem("排队中..."))
 
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
        pdf_to_image_files_exist = self.pdf_to_image_table.rowCount() > 0
        self.pdf_to_image_button.setEnabled(enable_when_not_running and pdf_to_image_files_exist)
        self.pdf_to_image_clear_button.setEnabled(enable_when_not_running and pdf_to_image_files_exist)
        self.pdf_to_image_stop_button.setEnabled(is_task_running)
        self.image_format_combo.setEnabled(enable_when_not_running)
        self.dpi_combo.setEnabled(enable_when_not_running)
        split_files_exist = self.split_table.rowCount() > 0
        self.split_button.setEnabled(enable_when_not_running and split_files_exist)
        self.split_clear_button.setEnabled(enable_when_not_running and split_files_exist)
        self.split_stop_button.setEnabled(is_task_running)
        bookmark_files_exist = self.bookmark_file_table.rowCount() > 0
        self.bookmark_select_button.setEnabled(enable_when_not_running)
        self.bookmark_clear_button.setEnabled(enable_when_not_running and bookmark_files_exist)
        self.use_common_bookmarks_checkbox.setEnabled(enable_when_not_running)
        self.add_new_bookmark_button.setEnabled(enable_when_not_running and bookmark_files_exist)
        self.edit_common_bookmarks_button.setEnabled(enable_when_not_running and bookmark_files_exist)
        self.import_bookmarks_button.setEnabled(enable_when_not_running)
        self.export_bookmarks_button.setEnabled(enable_when_not_running and bookmark_files_exist)
        self.bookmark_start_button.setEnabled(enable_when_not_running and bookmark_files_exist)
        self.bookmark_stop_button.setEnabled(is_task_running)
        self.select_button.setEnabled(enable_when_not_running)
        self.merge_select_button.setEnabled(enable_when_not_running)
        self.curves_select_button.setEnabled(enable_when_not_running)
        self.pdf_to_image_select_button.setEnabled(enable_when_not_running)
        self.split_select_button.setEnabled(enable_when_not_running)
        self.bookmark_select_button.setEnabled(enable_when_not_running)
        ocr_files_exist = self.ocr_table.rowCount() > 0
        self.ocr_select_button.setEnabled(enable_when_not_running)
        self.ocr_start_button.setEnabled(enable_when_not_running and ocr_files_exist)
        self.ocr_stop_button.setEnabled(is_task_running)
        self.ocr_clear_button.setEnabled(enable_when_not_running and ocr_files_exist)
    def start_optimization(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先选择要优化的PDF文件。")
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
            CustomMessageBox.warning(self, "警告", "请先选择要转曲的PDF文件。")
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
    def start_pdf_to_image_conversion(self):
        if self.pdf_to_image_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先选择要转换的PDF文件。")
            return
        output_dir = QFileDialog.getExistingDirectory(self, "选择图片保存文件夹")
        if not output_dir:
            return
        self._reset_pdf_to_image_ui()
        self._update_controls_state(is_task_running=True)
        files = [self.pdf_to_image_table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.pdf_to_image_table.rowCount())]
        image_format = self.image_format_combo.currentText().lower()
        dpi = int(self.dpi_combo.currentText())
        self.pdf_to_image_worker = PdfToImageWorker(files, output_dir, image_format, dpi)
        self.pdf_to_image_worker.total_progress.connect(self.pdf_to_image_progress_bar.setValue)
        self.pdf_to_image_worker.progress_updated.connect(self.on_pdf_to_image_progress)
        self.pdf_to_image_worker.file_finished.connect(self.on_pdf_to_image_file_finished)
        self.pdf_to_image_worker.finished.connect(self.on_pdf_to_image_all_finished)
        self.pdf_to_image_worker.start()
        self.status_label.setText("正在将PDF转换为图片...")
    def start_split(self):
        if self.split_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先选择要分割的PDF文件。")
            return
        output_dir = QFileDialog.getExistingDirectory(self, "选择分割后文件的保存文件夹")
        if not output_dir:
            return
        self._reset_split_ui()
        self._update_controls_state(is_task_running=True)
        files = [self.split_table.item(i, 0).data(Qt.ItemDataRole.UserRole) for i in range(self.split_table.rowCount())]
        self.split_worker = SplitWorker(files, output_dir)
        self.split_worker.total_progress.connect(self.split_progress_bar.setValue)
        self.split_worker.progress_updated.connect(self.on_split_progress)
        self.split_worker.file_finished.connect(self.on_split_file_finished)
        self.split_worker.finished.connect(self.on_split_all_finished)
        self.split_worker.start()
        self.status_label.setText("正在分割PDF文件...")
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
            CustomMessageBox.warning(self, "优化失败", f"文件处理失败：\n{error_message}")
            
    def on_curves_file_finished(self, row, result):
        if result.get("success"):
            self.curves_table.setItem(row, 2, QTableWidgetItem("转曲成功"))
        else:
            self.curves_table.setItem(row, 2, QTableWidgetItem("转曲失败"))
            error_message = result.get("message", "未知错误")
            self.curves_table.item(row, 2).setToolTip(error_message)
            CustomMessageBox.warning(self, "转曲失败", f"文件处理失败：\n{error_message}")
    def on_pdf_to_image_file_finished(self, row, result):
        if result.get("success"):
            self.pdf_to_image_table.setItem(row, 1, QTableWidgetItem("转换成功"))
            self.pdf_to_image_table.item(row, 1).setToolTip(result.get("message"))
        else:
            self.pdf_to_image_table.setItem(row, 1, QTableWidgetItem("转换失败"))
            error_message = result.get("message", "未知错误")
            self.pdf_to_image_table.item(row, 1).setToolTip(error_message)
            CustomMessageBox.warning(self, "转换失败", f"文件处理失败：\n{error_message}")
    def on_pdf_to_image_progress(self, file_index, current_page, total_pages):
        if total_pages > 0:
            progress_percentage = int((current_page / total_pages) * 100)
            self.pdf_to_image_table.setItem(file_index, 1, QTableWidgetItem(f"转换中... {progress_percentage}%"))
    def on_split_file_finished(self, row, result):
        if result.get("success"):
            self.split_table.setItem(row, 1, QTableWidgetItem("分割成功"))
            self.split_table.item(row, 1).setToolTip(result.get("message"))
        else:
            self.split_table.setItem(row, 1, QTableWidgetItem("分割失败"))
            error_message = result.get("message", "未知错误")
            self.split_table.item(row, 1).setToolTip(error_message)
            CustomMessageBox.warning(self, "分割失败", f"文件处理失败：\n{error_message}")
    def on_split_progress(self, file_index, current_page, total_pages):
        if total_pages > 0:
            progress_percentage = int((current_page / total_pages) * 100)
            self.split_table.setItem(file_index, 1, QTableWidgetItem(f"分割中... {progress_percentage}%"))
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
    def on_pdf_to_image_all_finished(self):
        self.status_label.setText("PDF转图片完成！")
        self.pdf_to_image_progress_bar.setValue(100)
        self._update_controls_state()
    def on_split_all_finished(self):
        self.status_label.setText("PDF分割完成！")
        self.split_progress_bar.setValue(100)
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
        elif current_tab == 3:
            self.pdf_to_image_table.setRowCount(0)
            self.pdf_to_image_progress_bar.setValue(0)
            self.status_label.setText("请选择要转换为图片的PDF文件...")
        elif current_tab == 4:
            self.split_table.setRowCount(0)
            self.split_progress_bar.setValue(0)
            self.status_label.setText("请选择要分割的PDF文件...")
        elif current_tab == 5: # Bookmark tab
            self.bookmark_file_table.setRowCount(0)
            self.bookmark_progress_bar.setValue(0)
            self.status_label.setText("请选择要添加书签的PDF文件...")
        elif current_tab == 6: # OCR tab
            self.ocr_table.setRowCount(0)
            self.ocr_progress_bar.setValue(0)
            self.ocr_result_text.clear()
            self.status_label.setText("请选择要进行OCR识别的PDF文件...")
        self._update_controls_state()
    def show_about_dialog(self):
        about_text = f"""
<div style='color:#333333;'>
    <p style='font-size:14pt; font-weight:bold; text-align:center;'>PDF Optimizer</p>
    <p style='font-size:10pt; text-align:center;'>一个功能强大的PDF处理工具</p>
    <hr>
    <p style='font-size:10pt;'><b>版本:</b> {self.app_version}</p>
    <p style='font-size:10pt;'><b>作者:</b> WanderInDoor</p>
    <p style='font-size:10pt;'><b>联系方式:</b> 76757488@qq.com</p>
    <p style='font-size:10pt;'><b>源代码:</b> <a href="https://github.com/ourpurple/PDFOptimizer">https://github.com/ourpurple/PDFOptimizer</a></p>
    <hr>
    <p style='font-size:10pt;'><b>主要功能:</b></p>
    <ul style='font-size:9pt;'>
        <li>PDF优化（压缩）</li>
        <li>PDF合并与分割</li>
        <li>PDF转图片</li>
        <li>PDF转曲（字体轮廓化）</li>
        <li>PDF书签管理</li>
        <li>PDF OCR识别（支持AI模型）</li>
    </ul>
    <hr>
    <p style='font-size:8pt; color:grey;'>基于 PySide6, Pikepdf, PyMuPDF 和 Ghostscript 构建</p>
</div>
"""
        CustomMessageBox.about(self, "关于 PDF Optimizer", about_text)

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

    def check_pandoc(self):
        """检查 pandoc 是否已安装，并更新状态标签。"""
        self.pandoc_installed = is_pandoc_installed()
        if self.pandoc_installed:
            self.pandoc_status_label.setText("✅ Pandoc 已安装")
            self.pandoc_status_label.setStyleSheet("color: green;")
        else:
            self.pandoc_status_label.setText("❌ 未找到 Pandoc (部分功能受限)")
            self.pandoc_status_label.setStyleSheet("color: red;")
            
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
            elif current_tab == 3:
                self.add_files_to_pdf_to_image(files)
            elif current_tab == 4:
                self.add_files_to_split(files)
            elif current_tab == 5: # Bookmark tab
                self.add_files_to_bookmark(files)
            elif current_tab == 6:
                self.add_files_to_ocr(files)
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
            CustomMessageBox.warning(self, "错误", "未检测到Ghostscript，无法使用转曲功能。")
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
    def add_files_to_pdf_to_image(self, files):
        current_row = self.pdf_to_image_table.rowCount()
        self.pdf_to_image_table.setRowCount(current_row + len(files))
        for i, file_path in enumerate(files):
            row = current_row + i
            self.pdf_to_image_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.pdf_to_image_table.setItem(row, 1, QTableWidgetItem("等待中..."))
            self.pdf_to_image_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)
        
        self.status_label.setText(f"已添加 {len(files)} 个文件到转换列表。")
        self._update_controls_state()
    def add_files_to_split(self, files):
        current_row = self.split_table.rowCount()
        self.split_table.setRowCount(current_row + len(files))
        for i, file_path in enumerate(files):
            row = current_row + i
            self.split_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.split_table.setItem(row, 1, QTableWidgetItem("等待中..."))
            self.split_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)
        
        self.status_label.setText(f"已添加 {len(files)} 个文件到分割列表。")
        self._update_controls_state()
    def add_files_to_bookmark(self, files):
        current_row = self.bookmark_file_table.rowCount()
        self.bookmark_file_table.setRowCount(current_row + len(files))
        for i, file_path in enumerate(files):
            row = current_row + i
            self.bookmark_file_table.setItem(row, 0, QTableWidgetItem(os.path.basename(file_path)))
            self.bookmark_file_table.setItem(row, 1, QTableWidgetItem("排队中..."))
            self.bookmark_file_table.setItem(row, 2, QTableWidgetItem("操作"))
            self.bookmark_file_table.item(row, 0).setData(Qt.ItemDataRole.UserRole, file_path)
        
        self.status_label.setText(f"已添加 {len(files)} 个文件到书签列表。")
        self._update_controls_state()
    def closeEvent(self, event):
        if hasattr(self, 'optimize_worker') and self.optimize_worker.isRunning():
            self.optimize_worker.stop()
        if hasattr(self, 'merge_worker') and self.merge_worker.isRunning():
            self.merge_worker.stop()
        if hasattr(self, 'curves_worker') and self.curves_worker.isRunning():
            self.curves_worker.stop()
        if hasattr(self, 'pdf_to_image_worker') and self.pdf_to_image_worker.isRunning():
            self.pdf_to_image_worker.stop()
        if hasattr(self, 'split_worker') and self.split_worker.isRunning():
            self.split_worker.stop()
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
        elif current_tab == 3 and hasattr(self, 'pdf_to_image_worker') and self.pdf_to_image_worker.isRunning():
            self.pdf_to_image_worker.stop()
            self.status_label.setText("转换任务已停止")
        elif current_tab == 4 and hasattr(self, 'split_worker') and self.split_worker.isRunning():
            self.split_worker.stop()
            self.status_label.setText("分割任务已停止")
        elif current_tab == 5 and hasattr(self, 'bookmark_worker') and self.bookmark_worker.isRunning(): # Bookmark tab
            self.bookmark_worker.stop()
            self.status_label.setText("添加书签任务已停止")
        elif current_tab == 6 and hasattr(self, 'ocr_worker') and self.ocr_worker.isRunning():
            self.ocr_worker.stop()
            self.status_label.setText("OCR 任务已停止")
        self._update_controls_state(is_task_running=False)
    def start_merge_pdfs(self):
        if self.merge_table.rowCount() < 2:
            CustomMessageBox.warning(self, "警告", "请至少选择两个PDF文件进行合并。")
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
            CustomMessageBox.information(self, "成功", f"文件已成功合并到:\n{result.get('output_path')}")
        else:
            for r in range(self.merge_table.rowCount()):
                self.merge_table.setItem(r, 1, QTableWidgetItem("合并失败"))
            error_message = result.get("message", "未知错误")
            CustomMessageBox.warning(self, "合并失败", f"合并失败：\n{error_message}")
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
    def _setup_pdf_to_image_tab(self):
        pdf_to_image_layout = QVBoxLayout(self.pdf_to_image_tab)
        file_select_layout = QHBoxLayout()
        self.pdf_to_image_select_button = QPushButton("选择PDF文件")
        self.pdf_to_image_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.pdf_to_image_select_button)
        file_select_layout.addStretch()
        pdf_to_image_layout.addLayout(file_select_layout)
        self.pdf_to_image_table = SortableTableWidget()
        self.pdf_to_image_table.setColumnCount(2)
        self.pdf_to_image_table.setHorizontalHeaderLabels(["文件名", "状态"])
        self.pdf_to_image_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.pdf_to_image_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.pdf_to_image_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        pdf_to_image_layout.addWidget(self.pdf_to_image_table)
        self.pdf_to_image_progress_bar = QProgressBar()
        self.pdf_to_image_progress_bar.setAlignment(Qt.AlignCenter)
        pdf_to_image_layout.addWidget(self.pdf_to_image_progress_bar)
        controls_layout = QHBoxLayout()
        image_format_label = QLabel("图片格式:")
        controls_layout.addWidget(image_format_label)
        self.image_format_combo = QComboBox()
        self.image_format_combo.addItems(["JPG", "PNG"])
        controls_layout.addWidget(self.image_format_combo)
        dpi_label = QLabel("分辨率 (DPI):")
        controls_layout.addWidget(dpi_label)
        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["72", "96", "150", "300", "600"])
        self.dpi_combo.setCurrentText("300")
        controls_layout.addWidget(self.dpi_combo)
        controls_layout.addStretch()
        self.pdf_to_image_clear_button = QPushButton("清空列表")
        self.pdf_to_image_clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.pdf_to_image_clear_button)
        self.pdf_to_image_button = QPushButton("开始转换")
        self.pdf_to_image_button.clicked.connect(self.start_pdf_to_image_conversion)
        controls_layout.addWidget(self.pdf_to_image_button)
        self.pdf_to_image_stop_button = QPushButton("停止")
        self.pdf_to_image_stop_button.clicked.connect(self.stop_current_task)
        controls_layout.addWidget(self.pdf_to_image_stop_button)
        
        pdf_to_image_layout.addLayout(controls_layout)
    def _setup_split_tab(self):
        split_layout = QVBoxLayout(self.split_tab)
        file_select_layout = QHBoxLayout()
        self.split_select_button = QPushButton("选择PDF文件")
        self.split_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.split_select_button)
        file_select_layout.addStretch()
        split_layout.addLayout(file_select_layout)
        self.split_table = SortableTableWidget()
        self.split_table.setColumnCount(2)
        self.split_table.setHorizontalHeaderLabels(["文件名", "状态"])
        self.split_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.split_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.split_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        split_layout.addWidget(self.split_table)
        self.split_progress_bar = QProgressBar()
        self.split_progress_bar.setAlignment(Qt.AlignCenter)
        split_layout.addWidget(self.split_progress_bar)
        controls_layout = QHBoxLayout()
        controls_layout.addStretch()
        self.split_clear_button = QPushButton("清空列表")
        self.split_clear_button.clicked.connect(self.clear_current_list)
        controls_layout.addWidget(self.split_clear_button)
        self.split_button = QPushButton("开始分割")
        self.split_button.clicked.connect(self.start_split)
        controls_layout.addWidget(self.split_button)
        self.split_stop_button = QPushButton("停止")
        self.split_stop_button.clicked.connect(self.stop_current_task)
        controls_layout.addWidget(self.split_stop_button)
        
        split_layout.addLayout(controls_layout)
    def _setup_bookmark_tab(self):
        layout = QVBoxLayout(self.bookmark_tab)
        # 文件选择区
        file_select_layout = QHBoxLayout()
        self.bookmark_select_button = QPushButton("选择PDF文件")
        self.bookmark_select_button.clicked.connect(self.select_files)
        file_select_layout.addWidget(self.bookmark_select_button)
        file_select_layout.addStretch()
        layout.addLayout(file_select_layout)
        # 文件列表表格
        self.bookmark_file_table = SortableTableWidget()
        self.bookmark_file_table.setColumnCount(3)
        self.bookmark_file_table.setHorizontalHeaderLabels(["文件名", "书签数", "操作"])
        self.bookmark_file_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.bookmark_file_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.bookmark_file_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        layout.addWidget(self.bookmark_file_table)
        # 共用书签模式切换
        mode_layout = QHBoxLayout()
        self.use_common_bookmarks_checkbox = QCheckBox("为所有文件添加同一组书签")
        mode_layout.addWidget(self.use_common_bookmarks_checkbox)
        mode_layout.addStretch()
        layout.addLayout(mode_layout)
        # 书签编辑/导入/导出区
        bookmark_ctrl_layout = QHBoxLayout()
        
        self.add_new_bookmark_button = QPushButton("新增书签")
        self.add_new_bookmark_button.clicked.connect(self.add_new_bookmark_clicked)
        bookmark_ctrl_layout.addWidget(self.add_new_bookmark_button)
        
        self.edit_common_bookmarks_button = QPushButton("编辑书签")
        self.edit_common_bookmarks_button.clicked.connect(self.edit_bookmarks_clicked)
        bookmark_ctrl_layout.addWidget(self.edit_common_bookmarks_button)
        
        self.import_bookmarks_button = QPushButton("导入书签配置")
        self.import_bookmarks_button.clicked.connect(self.import_bookmarks_clicked)
        bookmark_ctrl_layout.addWidget(self.import_bookmarks_button)
        
        self.export_bookmarks_button = QPushButton("导出书签配置")
        self.export_bookmarks_button.clicked.connect(self.export_bookmarks_clicked)
        bookmark_ctrl_layout.addWidget(self.export_bookmarks_button)
        
        bookmark_ctrl_layout.addStretch()
        layout.addLayout(bookmark_ctrl_layout)
        # 进度条和开始按钮
        progress_layout = QHBoxLayout()
        self.bookmark_progress_bar = QProgressBar()
        self.bookmark_progress_bar.setAlignment(Qt.AlignCenter)
        progress_layout.addWidget(self.bookmark_progress_bar)
        
        self.bookmark_clear_button = QPushButton("清空列表")
        self.bookmark_clear_button.clicked.connect(self.clear_current_list)
        progress_layout.addWidget(self.bookmark_clear_button)
        
        self.bookmark_start_button = QPushButton("开始添加书签")
        self.bookmark_start_button.clicked.connect(self.start_add_bookmarks)
        progress_layout.addWidget(self.bookmark_start_button)
        
        self.bookmark_stop_button = QPushButton("停止")
        self.bookmark_stop_button.clicked.connect(self.stop_current_task)
        progress_layout.addWidget(self.bookmark_stop_button)
        
        layout.addLayout(progress_layout)
    def _setup_tab_connections(self):
        """设置标签页切换事件连接"""
        self.tab_widget.currentChanged.connect(lambda: self._update_controls_state())
    def edit_bookmarks_clicked(self):
        use_common = self.use_common_bookmarks_checkbox.isChecked()
        if use_common:
            # 编辑共用书签
            if not hasattr(self, '_common_bookmarks'):
                self._common_bookmarks = []
            dlg = BookmarkEditDialog(self, bookmarks=self._common_bookmarks)
            if dlg.exec() == QDialog.Accepted:
                self._common_bookmarks = dlg.get_bookmarks()
        else:
            # 编辑选中文件的书签
            selected = self.bookmark_file_table.selectedItems()
            if not selected:
                CustomMessageBox.warning(self, "提示", "请先选中要编辑书签的文件！")
                return
            row = selected[0].row()
            file_path = self.bookmark_file_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if not hasattr(self, '_file_bookmarks'):
                self._file_bookmarks = {}
            bookmarks = self._file_bookmarks.get(file_path, [])
            dlg = BookmarkEditDialog(self, bookmarks=bookmarks)
            if dlg.exec() == QDialog.Accepted:
                self._file_bookmarks[file_path] = dlg.get_bookmarks()
                self.bookmark_file_table.setItem(row, 1, QTableWidgetItem(str(len(self._file_bookmarks[file_path]))))
    def import_bookmarks_clicked(self):
        path, _ = QFileDialog.getOpenFileName(self, "导入书签配置", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            if 'all' in data:
                self._common_bookmarks = data['all']
                self.use_common_bookmarks_checkbox.setChecked(True)
            else:
                self._file_bookmarks = data
                self.use_common_bookmarks_checkbox.setChecked(False)
            # 更新界面书签数
            for row in range(self.bookmark_file_table.rowCount()):
                file_path = self.bookmark_file_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
                if hasattr(self, '_file_bookmarks') and file_path in self._file_bookmarks:
                    self.bookmark_file_table.setItem(row, 1, QTableWidgetItem(str(len(self._file_bookmarks[file_path]))))
                elif hasattr(self, '_common_bookmarks'):
                    self.bookmark_file_table.setItem(row, 1, QTableWidgetItem(str(len(self._common_bookmarks))))
        except Exception as e:
            CustomMessageBox.warning(self, "导入失败", f"导入书签配置失败：{str(e)}")
    def export_bookmarks_clicked(self):
        path, _ = QFileDialog.getSaveFileName(self, "导出书签配置", "", "JSON Files (*.json)")
        if not path:
            return
        try:
            if self.use_common_bookmarks_checkbox.isChecked():
                data = {'all': getattr(self, '_common_bookmarks', [])}
            else:
                data = getattr(self, '_file_bookmarks', {})
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            CustomMessageBox.information(self, "导出成功", "书签配置已成功导出！")
        except Exception as e:
            CustomMessageBox.warning(self, "导出失败", f"导出书签配置失败：{str(e)}")
    def start_add_bookmarks(self):
        """开始添加书签到PDF文件"""
        if self.bookmark_file_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先选择要添加书签的PDF文件。")
            return
        # 获取所有文件路径和它们的目录
        file_paths = []
        output_dir = None
        for row in range(self.bookmark_file_table.rowCount()):
            file_path = self.bookmark_file_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            file_paths.append(file_path)
            if output_dir is None:
                output_dir = os.path.dirname(file_path)
            elif output_dir != os.path.dirname(file_path):
                # 如果文件来自不同目录，则弹出选择框
                output_dir = QFileDialog.getExistingDirectory(self, "选择添加书签后文件的保存文件夹")
                if not output_dir:
                    return
                break
        use_common = self.use_common_bookmarks_checkbox.isChecked()
        # 构建 file_bookmarks
        file_bookmarks = {}
        for file_path in file_paths:
            if use_common:
                file_bookmarks[file_path] = getattr(self, '_common_bookmarks', [])
            else:
                file_bookmarks[file_path] = getattr(self, '_file_bookmarks', {}).get(file_path, [])
        if use_common and not getattr(self, '_common_bookmarks', []):
            CustomMessageBox.warning(self, "警告", "请先编辑共用书签！")
            return
        if not use_common and not any(file_bookmarks.values()):
            CustomMessageBox.warning(self, "警告", "请为每个文件编辑书签！")
            return
        self._reset_bookmark_ui()
        self._update_controls_state(is_task_running=True)
        self.bookmark_worker = AddBookmarkWorker(file_bookmarks, output_dir, use_common, getattr(self, '_common_bookmarks', []))
        self.bookmark_worker.progress.connect(self.bookmark_progress_bar.setValue)
        self.bookmark_worker.file_finished.connect(self.on_bookmark_file_finished)
        self.bookmark_worker.finished.connect(self.on_bookmark_all_finished)
        self.bookmark_worker.start()
        self.status_label.setText("正在批量添加书签...")
    def on_bookmark_file_finished(self, row, result):
        """处理单个文件的书签添加结果"""
        if result.get("success"):
            self.bookmark_file_table.setItem(row, 2, QTableWidgetItem("添加成功"))
            # 显示输出文件路径
            output_path = result.get("output", "")
            if output_path:
                self.bookmark_file_table.item(row, 2).setToolTip(f"已保存到：{output_path}")
        else:
            self.bookmark_file_table.setItem(row, 2, QTableWidgetItem("添加失败"))
            error_message = result.get("message", "未知错误")
            self.bookmark_file_table.item(row, 2).setToolTip(error_message)
            CustomMessageBox.warning(
                self, 
                "添加失败", 
                f"文件 {os.path.basename(result.get('file', ''))} 处理失败：\n{error_message}"
            )
    def on_bookmark_all_finished(self):
        self.status_label.setText("书签批量添加完成！")
        self.bookmark_progress_bar.setValue(100)
        self._update_controls_state()
    def add_new_bookmark_clicked(self):
        """处理新增书签按钮点击事件"""
        use_common = self.use_common_bookmarks_checkbox.isChecked()
        if use_common:
            # 编辑共用书签
            if not hasattr(self, '_common_bookmarks'):
                self._common_bookmarks = []
            dlg = BookmarkEditDialog(self, bookmarks=self._common_bookmarks, is_new=True)
            if dlg.exec() == QDialog.Accepted:
                self._common_bookmarks = dlg.get_bookmarks()
        else:
            # 编辑选中文件的书签
            selected = self.bookmark_file_table.selectedItems()
            if not selected:
                CustomMessageBox.warning(self, "提示", "请先选中要添加书签的文件！")
                return
            row = selected[0].row()
            file_path = self.bookmark_file_table.item(row, 0).data(Qt.ItemDataRole.UserRole)
            if not hasattr(self, '_file_bookmarks'):
                self._file_bookmarks = {}
            bookmarks = self._file_bookmarks.get(file_path, [])
            dlg = BookmarkEditDialog(self, bookmarks=bookmarks, is_new=True)
            if dlg.exec() == QDialog.Accepted:
                self._file_bookmarks[file_path] = dlg.get_bookmarks()
                self.bookmark_file_table.setItem(row, 1, QTableWidgetItem(str(len(self._file_bookmarks[file_path]))))
    def add_files_to_ocr(self, files):
        if not files:
            return
        if len(files) > 1:
            CustomMessageBox.information(self, "提示", "OCR 功能每次仅能处理一个PDF文件，将只添加第一个文件。")

        file_path = files[0]  # 只取第一个文件
        self.ocr_table.setRowCount(1)
        self.ocr_table.setItem(0, 0, QTableWidgetItem(os.path.basename(file_path)))
        self.ocr_table.setItem(0, 1, QTableWidgetItem("等待中..."))
        self.ocr_table.item(0, 0).setData(Qt.ItemDataRole.UserRole, file_path)
        
        self.status_label.setText(f"已添加文件: {os.path.basename(file_path)}")
        self._reset_ocr_ui()
        self._update_controls_state()
    def _setup_ocr_tab(self):
        ocr_layout = QVBoxLayout(self.ocr_tab)
        
        # --- Top Controls ---
        top_controls_layout = QHBoxLayout()
        self.ocr_select_button = QPushButton("选择PDF文件 (仅限单个)")
        self.ocr_select_button.clicked.connect(self.select_files)
        top_controls_layout.addWidget(self.ocr_select_button)
        
        # 添加配置按钮
        self.ocr_config_button = QPushButton("配置...")
        self.ocr_config_button.clicked.connect(self._open_ocr_config_dialog)
        top_controls_layout.addWidget(self.ocr_config_button)
        
        top_controls_layout.addStretch()
        ocr_layout.addLayout(top_controls_layout)
        
        # --- File Table ---
        self.ocr_table = SortableTableWidget()
        self.ocr_table.setColumnCount(2)
        self.ocr_table.setHorizontalHeaderLabels(["文件名", "状态"])
        # 设置两列各占50%的宽度
        self.ocr_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.ocr_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.Stretch)
        self.ocr_table.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.ocr_table.setEditTriggers(QAbstractItemView.NoEditTriggers)
        ocr_layout.addWidget(self.ocr_table)
        
        # --- Result Display ---
        self.ocr_result_text = QTextEdit()
        self.ocr_result_text.setReadOnly(True)
        self.ocr_result_text.setPlaceholderText("OCR识别结果将显示在这里...")
        ocr_layout.addWidget(self.ocr_result_text)
        
        # --- Progress Bar and Bottom Controls ---
        self.ocr_progress_bar = QProgressBar()
        self.ocr_progress_bar.setAlignment(Qt.AlignCenter)
        ocr_layout.addWidget(self.ocr_progress_bar)
        
        bottom_controls_layout = QHBoxLayout()
        bottom_controls_layout.addStretch()
        self.ocr_clear_button = QPushButton("清空列表")
        self.ocr_clear_button.clicked.connect(self.clear_current_list)
        self.ocr_start_button = QPushButton("开始识别")
        self.ocr_start_button.clicked.connect(self.start_ocr_conversion)
        self.ocr_stop_button = QPushButton("停止")
        self.ocr_stop_button.clicked.connect(self.stop_current_task)
        bottom_controls_layout.addWidget(self.ocr_clear_button)
        bottom_controls_layout.addWidget(self.ocr_start_button)
        bottom_controls_layout.addWidget(self.ocr_stop_button)
        ocr_layout.addLayout(bottom_controls_layout)
    def _load_config(self):
        self.env_path = os.path.join(os.path.expanduser("~"), ".pdfoptimizer", ".env")
        if not os.path.exists(os.path.dirname(self.env_path)):
             os.makedirs(os.path.dirname(self.env_path))
        dotenv.load_dotenv(dotenv_path=self.env_path)

    def _save_config(self):
        # 配置现在由 OcrConfigDialog 管理，此处留空但保留方法以避免破坏其他代码
        pass
    def start_ocr_conversion(self):
        if self.ocr_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先选择一个PDF文件进行OCR识别。")
            return

        # 检查 Pandoc 是否安装，并引导用户
        if not self.pandoc_installed:
            reply = CustomMessageBox.question(
                self,
                "依赖缺失",
                "检测到 Pandoc 未安装，OCR结果将无法自动转换为.docx文件。\n\n"
                "Pandoc 是一个强大的文档转换工具，建议从其官网 pandoc.org 下载并安装。\n\n"
                "是否要继续（仅生成 .md 文件）？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
            
        # 从 .env 文件重新加载配置
        if os.path.exists(self.env_path):
            dotenv.load_dotenv(dotenv_path=self.env_path, override=True)
            
        api_provider = os.getenv("OCR_API_PROVIDER", "OpenAI-Compatible")

        if api_provider == "Mistral API":
            api_key = os.getenv("MISTRAL_API_KEY", "")
            model_name = os.getenv("MISTRAL_MODEL_NAME", "mistral-ocr-latest")
        else:
            api_key = os.getenv("OPENAI_API_KEY", "")
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

        if not api_key:
            CustomMessageBox.warning(self, "警告", f"请在配置对话框中为 {api_provider} 设置API Key。")
            self._open_ocr_config_dialog() # 引导用户去配置
            return
            
        self._reset_ocr_ui()
        # 清空预览内容
        if hasattr(self, 'ocr_worker'):
            self.ocr_worker.preview_content = ""
        self.ocr_result_text.clear()
        self._update_controls_state(is_task_running=True)
        file_path_data = self.ocr_table.item(0, 0).data(Qt.ItemDataRole.UserRole)

        if not file_path_data:
            CustomMessageBox.warning(self, "错误", "无法获取文件路径。")
            self._update_controls_state(is_task_running=False)
            return
        
        # 从环境变量获取配置
        api_base_url = os.getenv("OCR_API_BASE_URL", "https://api.openai.com/v1")
        prompt_text = os.getenv("OCR_PROMPT", "这是一个PDF页面。请准确识别所有内容，并将其转换为结构良好的Markdown格式。")
        # 获取温度参数，默认值为1.0
        temperature = float(os.getenv("OCR_TEMPERATURE", "1.0"))
        
        self.ocr_worker = OcrWorker(
            file_path=file_path_data,
            api_key=api_key,
            model_name=model_name,
            api_base_url=api_base_url,
            prompt_text=prompt_text,
            temp_dir=self.temp_dir,
            api_provider=api_provider,
            temperature=temperature  # 传递温度参数
        )
        self.ocr_worker.total_progress.connect(self.ocr_progress_bar.setValue)
        self.ocr_worker.ocr_progress.connect(lambda msg: self.ocr_table.setItem(0, 1, QTableWidgetItem(msg)))
        self.ocr_worker.preview_updated.connect(self.ocr_result_text.setPlainText)  # 连接预览更新信号
        self.ocr_worker.ocr_finished.connect(self.on_ocr_finished)
        self.ocr_worker.finished.connect(lambda: self._update_controls_state(is_task_running=False))
        self.ocr_worker.start()
        self.status_label.setText(f"正在使用 {api_provider} - {model_name} 进行OCR识别...")
        


    def on_ocr_finished(self, result):
        logger = result.get("logger", logging.getLogger(__name__))
        
        if result.get("success"):
            markdown_content = result.get("markdown_content", "")
            logger.info(f"接收到OCR结果，原始内容长度: {len(markdown_content)} 字符。")
            
            self.ocr_result_text.setPlainText(markdown_content)
            self.ocr_table.setItem(0, 1, QTableWidgetItem("识别成功"))
            
            # 自动保存逻辑
            try:
                file_path_data = self.ocr_table.item(0, 0).data(Qt.ItemDataRole.UserRole)
                if not file_path_data:
                    raise Exception("无法获取原始文件路径。")

                base_name_with_ext = os.path.basename(file_path_data)
                base_name, _ = os.path.splitext(base_name_with_ext)
                output_dir = os.path.dirname(file_path_data)
                
                # 保存 Markdown 文件
                md_filename = f"{base_name}[ocr].md"
                md_save_path = os.path.join(output_dir, md_filename)
                with open(md_save_path, 'w', encoding='utf-8') as f:
                    f.write(markdown_content)
                logger.info(f"OCR结果已自动保存到: {md_save_path}")

                # 如果安装了 Pandoc，则保存 Word 文件
                docx_save_path = None
                if self.pandoc_installed:
                    docx_filename = f"{base_name}[ocr].docx"
                    docx_save_path = os.path.join(output_dir, docx_filename)
                    processed_content = preprocess_markdown_for_pandoc(markdown_content)
                    conversion_result = convert_markdown_to_docx_with_pandoc(processed_content, docx_save_path)
                    if conversion_result["success"]:
                        logger.info(f"OCR结果已自动转换为 DOCX: {docx_save_path}")
                    else:
                        logger.error(f"自动转换为 DOCX 失败: {conversion_result['message']}")
                        CustomMessageBox.warning(self, "Word 转换失败", f"无法将Markdown转换为Word文档。\n\nPandoc错误: {conversion_result['message']}")
                        docx_save_path = None
                else:
                    logger.warning("未检测到 Pandoc，跳过 DOCX 转换。")
                
                # 更新 UI 消息
                if docx_save_path:
                    save_message = f"结果已自动保存到：\n{md_save_path}\n{docx_save_path}"
                    self.status_label.setText("OCR成功！结果已自动保存为 MD 和 DOCX。")
                else:
                    save_message = f"结果已自动保存到：\n{md_save_path}"
                    self.status_label.setText("OCR成功！结果已自动保存为 MD。")
                
                CustomMessageBox.information(self, "识别成功", save_message)

            except Exception as e:
                error_msg = f"自动保存OCR结果时出错: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.status_label.setText("OCR识别完成，但自动保存失败。")
                CustomMessageBox.warning(self, "自动保存失败", f"OCR识别已完成，但自动保存文件时遇到错误。\n您仍然可以手动保存结果。\n\n错误详情: {error_msg}")
        
        else:
            error_message = result.get("message", "未知错误")
            self.ocr_table.setItem(0, 1, QTableWidgetItem("识别失败"))
            self.ocr_result_text.setText(f"发生错误:\n{error_message}")
            CustomMessageBox.warning(self, "识别失败", f"OCR处理失败:\n{error_message}")
            self.status_label.setText("OCR识别失败。")
    
    def _open_ocr_config_dialog(self):
        """打开OCR配置对话框"""
        # 导入配置对话框类
        from .ocr_config_dialog import OcrConfigDialog

        # 创建并显示对话框
        dialog = OcrConfigDialog(self)
        dialog.exec()  # 使用 exec() 以模态方式运行对话框


class AddBookmarkWorker(QThread):
    """书签添加工作线程"""
    progress = Signal(int)
    file_finished = Signal(int, dict)
    finished = Signal()

    def __init__(self, file_bookmarks, output_dir, use_common, common_bookmarks):
        super().__init__()
        self.file_bookmarks = file_bookmarks
        self.output_dir = output_dir
        self.use_common = use_common
        self.common_bookmarks = common_bookmarks
        self._is_running = True

    def run(self):
        files = list(self.file_bookmarks.keys())
        total = len(files)

        # 确保输出目录存在
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        # 批量添加书签
        results = batch_add_bookmarks_to_pdfs(
            self.file_bookmarks,
            self.output_dir,
            use_common=self.use_common,
            common_bookmarks=self.common_bookmarks
        )

        # 处理每个文件的结果
        for i, result in enumerate(results):
            if not self._is_running:
                break
            # 找到原始文件在files列表中的索引
            original_file_path = result.get('file')
            try:
                original_index = files.index(original_file_path)
                self.file_finished.emit(original_index, result)
            except ValueError:
                # 如果找不到文件，可以记录一个错误或忽略
                pass


            self.progress.emit(int((i + 1) / total * 100))

        self.finished.emit()

    def stop(self):
        self._is_running = False
