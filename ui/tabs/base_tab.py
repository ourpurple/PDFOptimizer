import os
from PySide6.QtWidgets import (
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QTableWidget,
    QProgressBar,
    QTableWidgetItem,
    QHeaderView,
)
from PySide6.QtCore import Signal, Qt
from ui import constants as const
from ui.custom_dialog import CustomMessageBox
from ui.widgets import SortableTableWidget


class BaseTabWidget(QWidget):
    """
    所有功能标签页的基类，封装了通用的UI元素和逻辑。
    """
    task_started = Signal()
    task_finished = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.worker = None
        self._is_task_running = False
        
        # 将UI设置和连接分开
        self._setup_ui()
        self._connect_signals()

    def _setup_ui(self):
        """创建通用的UI组件"""
        layout = QVBoxLayout(self)
        self.setLayout(layout) # 确保布局被设置

        # 1. 文件选择布局
        self.select_button = QPushButton(const.SELECT_PDF_BUTTON_TEXT)
        self.file_select_layout = QHBoxLayout()
        self.file_select_layout.addWidget(self.select_button)
        self.file_select_layout.addStretch()
        layout.addLayout(self.file_select_layout)

        # 2. 文件列表
        self.file_table = self._create_table_widget()
        layout.addWidget(self.file_table)

        # 3. 进度条和控制按钮
        self.progress_bar = QProgressBar()
        self.progress_bar.setAlignment(Qt.AlignCenter)
        
        progress_layout = QHBoxLayout()
        progress_layout.addWidget(self.progress_bar)

        self.clear_button = QPushButton(const.CLEAR_LIST_BUTTON_TEXT)
        self.start_button = QPushButton(const.START_BUTTON_TEXT)
        self.stop_button = QPushButton(const.STOP_BUTTON_TEXT)

        progress_layout.addWidget(self.clear_button)
        progress_layout.addWidget(self.start_button)
        progress_layout.addWidget(self.stop_button)
        layout.addLayout(progress_layout)
        
        # 为子类准备一个列表来存放它们自己的控件
        self.other_controls = []

    def _select_files(self):
        """处理文件选择逻辑"""
        from PySide6.QtWidgets import QFileDialog
        files, _ = QFileDialog.getOpenFileNames(self, const.SELECT_PDF_FILES, "", const.PDF_FILTER)
        if files:
            self.add_files(files)

    def _connect_signals(self):
        """连接信号和槽"""
        self.select_button.clicked.connect(self._select_files)
        self.clear_button.clicked.connect(self.clear_list)
        self.start_button.clicked.connect(self.start_task)
        self.stop_button.clicked.connect(self.stop_task)
        
        # 内部信号连接，用于自动更新控件状态
        self.task_started.connect(lambda: self.set_task_running(True))
        self.task_finished.connect(lambda msg: self.set_task_running(False))
        # 当表格内容改变时也更新状态
        self.file_table.model().rowsInserted.connect(lambda: self.update_controls_state())
        self.file_table.model().rowsRemoved.connect(lambda: self.update_controls_state())

    def set_task_running(self, is_running):
        """设置任务运行状态并更新UI"""
        self._is_task_running = is_running
        self.update_controls_state()
        # 通知主窗口，以便它可以更新全局控件（如标签页切换）
        if hasattr(self.main_window, 'on_task_state_changed'):
            self.main_window.on_task_state_changed(is_running)

    def update_controls_state(self):
        """
        更新此标签页内所有控件的启用/禁用状态。
        子类应该重写此方法，并首先调用 super().update_controls_state()。
        """
        is_running = self._is_task_running
        files_exist = self.file_table.rowCount() > 0
        
        self.select_button.setEnabled(not is_running)
        self.clear_button.setEnabled(not is_running and files_exist)
        self.start_button.setEnabled(not is_running and files_exist)
        self.stop_button.setEnabled(is_running)

        # 禁用/启用子类中定义的其他控件
        for control in self.other_controls:
            control.setEnabled(not is_running)

    def _create_table_widget(self):
        """创建一个标准的文件表格"""
        table = SortableTableWidget()
        # 基类不应该对列数或标题做任何假设
        # 子类应该负责设置这些
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        return table

    def add_files(self, files):
        """向文件列表中添加文件"""
        if not files:
            return
        
        # 子类应该重写此方法来添加具有正确列数的行
        # 这里提供一个非常基本的实现
        for file_path in files:
            row_count = self.file_table.rowCount()
            self.file_table.insertRow(row_count)
            item_name = QTableWidgetItem(os.path.basename(file_path))
            item_name.setData(Qt.UserRole, file_path)
            self.file_table.setItem(row_count, 0, item_name)
        
        self.main_window.status_label.setText(const.STATUS_LABEL_FILES_ADDED.format(count=len(files)))
        self.update_controls_state()

    def clear_list(self):
        """清空文件列表和重置进度条"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
        self.file_table.setRowCount(0)
        self.progress_bar.setValue(0)
        self.main_window.status_label.setText(const.STATUS_LABEL_CLEARED)
        self.update_controls_state()

    def start_task(self):
        """开始处理任务（由子类实现）"""
        raise NotImplementedError("Each tab must implement its own start_task method.")

    def stop_task(self):
        """停止当前任务"""
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.task_finished.emit(const.TASK_MANUALLY_STOPPED) # 发射信号以统一状态更新

    def get_file_list(self):
        """获取文件列表中的所有文件路径"""
        files = []
        for row in range(self.file_table.rowCount()):
            item = self.file_table.item(row, 0)
            if item:
                files.append(item.data(Qt.UserRole))
        return files