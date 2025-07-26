import sys
from PySide6.QtWidgets import (
    QMainWindow,
    QPushButton,
    QVBoxLayout,
    QWidget,
    QLabel,
    QFileDialog,
    QHBoxLayout,
    QTabWidget,
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtGui import QIcon
import os
import shutil
from ui import constants as const
from ui.tabs.optimize_tab import OptimizeTabWidget
from ui.tabs.merge_tab import MergeTabWidget
from ui.tabs.curves_tab import CurvesTabWidget
from ui.tabs.pdf_to_image_tab import PdfToImageTabWidget
from ui.tabs.split_tab import SplitTabWidget
from ui.tabs.bookmark_tab import BookmarkTabWidget
from ui.tabs.ocr_tab import OcrTabWidget
from core import (
    is_ghostscript_installed,
    is_pandoc_installed,
    __version__,
)
from .custom_dialog import CustomMessageBox


def resource_path(relative_path):
    """获取资源的绝对路径"""
    if hasattr(sys, "_MEIPASS"):
        return os.path.join(sys._MEIPASS, relative_path)
    return os.path.join(os.path.abspath("."), relative_path)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.app_version = f"v{__version__}"
        self.setWindowTitle(f"{const.MAIN_WINDOW_TITLE} - {self.app_version}")
        self.setGeometry(100, 100, 1080, 720)
        icon_path = resource_path("ui/app.ico")
        if os.path.exists(icon_path):
            self.setWindowIcon(QIcon(icon_path))
        self.setAcceptDrops(True)
        main_layout = QVBoxLayout()
        self.tab_widget = QTabWidget()
        self.tab_widget.setTabPosition(QTabWidget.TabPosition.North)
        self.optimize_tab = OptimizeTabWidget(self)
        self.merge_tab = MergeTabWidget(self)
        self.curves_tab = CurvesTabWidget(self)
        self.pdf_to_image_tab = PdfToImageTabWidget(self)
        self.split_tab = SplitTabWidget(self)
        self.bookmark_tab = BookmarkTabWidget(self)
        self.ocr_tab = OcrTabWidget(self)
        self.tab_widget.addTab(self.optimize_tab, const.OPTIMIZE_TAB_NAME)
        self.tab_widget.addTab(self.merge_tab, const.MERGE_TAB_NAME)
        self.tab_widget.addTab(self.curves_tab, const.CURVES_TAB_NAME)
        self.tab_widget.addTab(self.pdf_to_image_tab, const.PDF_TO_IMAGE_TAB_NAME)
        self.tab_widget.addTab(self.split_tab, const.SPLIT_TAB_NAME)
        self.tab_widget.addTab(self.bookmark_tab, const.BOOKMARK_TAB_NAME)
        self.tab_widget.addTab(self.ocr_tab, const.OCR_TAB_NAME)

        main_layout.addWidget(self.tab_widget)
        status_layout = QHBoxLayout()
        self.status_label = QLabel(const.DEFAULT_STATUS_TEXT) 
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        self.gs_status_label = QLabel()
        status_layout.addWidget(self.gs_status_label)

        self.pandoc_status_label = QLabel()
        status_layout.addWidget(self.pandoc_status_label)

        status_layout.addSpacing(20)
        self.about_button = QPushButton(const.ABOUT_BUTTON_TEXT)
        self.about_button.clicked.connect(self.show_about_dialog)
        status_layout.addWidget(self.about_button)
        main_layout.addLayout(status_layout)

        # Connect signals after status_label is created
        self.tab_widget.currentChanged.connect(self._on_tab_changed)
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, "task_finished"):
                tab.task_finished.connect(self.status_label.setText)

        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)
        self.apply_stylesheet()
        self.check_ghostscript()
        self.check_pandoc()
        self._on_tab_changed(0)  # Set initial status label

        self.temp_dir = os.path.join(os.path.expanduser("~"), ".pdfoptimizer", "temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
        qr = self.frameGeometry()
        cp = self.screen().availableGeometry().center()
        qr.moveCenter(cp)
        self.move(qr.topLeft())

    def _on_tab_changed(self, index):
        """当标签页切换时，更新状态栏文本"""
        tab_status_map = {
            0: "请选择需要优化的PDF文件",
            1: "请选择需要合并的PDF文件 (至少2个)",
            2: "请选择需要转曲的PDF文件",
            3: "请选择需要转换为图片的PDF文件",
            4: "请选择需要分割的PDF文件",
            5: "请选择需要添加书签的PDF文件",
            6: "请选择一个PDF文件进行OCR",
        }
        status_text = tab_status_map.get(index, const.DEFAULT_STATUS_TEXT)
        self.status_label.setText(status_text)

    def show_about_dialog(self):
        # About text might need constants that are not yet defined, so use hardcoded for now
        about_text = f"""
        <p><b>PDF Optimizer {self.app_version}</b></p>
        <p>作者: one-lazy-cat</p>
        <p>邮箱: one.lazy.cat@foxmail.com</p>
        <p>一个用于PDF处理的桌面工具。</p>
        <p><a href="https://github.com/one-lazy-cat/PDF-Optimizer">GitHub 项目地址</a></p>
        """
        CustomMessageBox.about(self, "关于 PDF Optimizer", about_text)

    def apply_stylesheet(self):
        style_path = resource_path("ui/style.qss")
        if os.path.exists(style_path):
            with open(style_path, "r", encoding="utf-8") as f:
                self.setStyleSheet(f.read())

    def check_ghostscript(self):
        gs_installed = is_ghostscript_installed()
        if gs_installed:
            self.gs_status_label.setText(const.GS_STATUS_LABEL_OK)
            self.gs_status_label.setStyleSheet("color: green;")
        else:
            self.gs_status_label.setText(const.GS_STATUS_LABEL_FAIL)
            self.gs_status_label.setStyleSheet("color: red;")

        # Notify relevant tabs
        if hasattr(self, 'optimize_tab'):
            self.optimize_tab.update_gs_status(gs_installed)
        if hasattr(self, 'merge_tab'):
            self.merge_tab.update_gs_status(gs_installed)
        if hasattr(self, 'curves_tab'):
            self.curves_tab.update_gs_status(gs_installed)

    def check_pandoc(self):
        """检查 pandoc 是否已安装，并更新状态标签。"""
        pandoc_installed = is_pandoc_installed()
        if pandoc_installed:
            self.pandoc_status_label.setText(const.PANDOC_STATUS_LABEL_OK)
            self.pandoc_status_label.setStyleSheet("color: green;")
        else:
            self.pandoc_status_label.setText(const.PANDOC_STATUS_LABEL_FAIL)
            self.pandoc_status_label.setStyleSheet("color: red;")
        
        if hasattr(self, 'ocr_tab'):
            self.ocr_tab.update_pandoc_status(pandoc_installed)


    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        files = []
        for url in event.mimeData().urls():
            file_path = url.toLocalFile()
            if file_path.lower().endswith(".pdf"):
                files.append(file_path)
        if files:
            self._add_files_to_current_tab(files)

    def _add_files_to_current_tab(self, files):
        """根据当前激活的标签页，将文件添加到对应的处理列表"""
        current_tab = self.tab_widget.widget(self.tab_widget.currentIndex())
        if hasattr(current_tab, "add_files"):
            # OCR tab handles single file logic internally
            if isinstance(current_tab, OcrTabWidget):
                current_tab.add_files(files)
            else:
                current_tab.add_files(files)

    def closeEvent(self, event):
        for i in range(self.tab_widget.count()):
            tab = self.tab_widget.widget(i)
            if hasattr(tab, "stop_task"):
                tab.stop_task()

        # 清理临时目录
        if hasattr(self, "temp_dir") and os.path.exists(self.temp_dir):
            try:
                shutil.rmtree(self.temp_dir)
            except Exception:
                pass

        event.accept()
