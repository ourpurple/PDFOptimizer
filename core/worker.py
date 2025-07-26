# -*- coding: utf-8 -*-
import logging
from PySide6.QtCore import QThread, Signal

class ProcessingWorker(QThread):
    """通用处理工作线程"""

    progress = Signal(int)  # 整体任务进度 (0-100)
    file_finished = Signal(int, dict)  # 单个文件处理完成 (文件索引, 结果字典)
    page_progress = Signal(int, int, int) # 单个文件内部分页进度 (文件索引, 当前页, 总页数)
    status_updated = Signal(str) # 状态文本更新 (例如 "正在转换...")
    preview_updated = Signal(str) # 预览内容更新 (例如 OCR 实时文本)
    finished = Signal()
    error = Signal(str)

    def __init__(self, target_function, *args, **kwargs):
        super().__init__()
        self.target_function = target_function
        self.args = args
        self.kwargs = kwargs
        self._is_running = True

    def run(self):
        try:
            if not self._is_running:
                return

            # 将 stop 方法和信号作为回调传递给目标函数
            # 这要求目标函数能够接受这些额外的关键字参数
            self.kwargs["worker_signals"] = {
                "progress": self.progress,
                "file_finished": self.file_finished,
                "page_progress": self.page_progress,
                "status_updated": self.status_updated,
                "preview_updated": self.preview_updated,
                "is_running": self.is_running,
            }

            self.target_function(*self.args, **self.kwargs)

        except Exception as e:
            logging.error(f"Worker-level error: {e}", exc_info=True)
            self.error.emit(str(e))
        finally:
            self.finished.emit()

    def stop(self):
        self._is_running = False

    def is_running(self):
        return self._is_running