import logging
import os
import shutil
from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QHeaderView,
    QMessageBox,
    QTableWidgetItem,
    QTextEdit,
)
import dotenv

from core import convert_markdown_to_docx_with_pandoc, preprocess_markdown_for_pandoc
from core.ocr import run_ocr_on_file
from core.worker import ProcessingWorker
from ui import constants as const
from ui.custom_dialog import CustomMessageBox
from ui.widgets import create_control_button
from ui.ocr_config_dialog import OcrConfigDialog
from ui.tabs.base_tab import BaseTabWidget


class OcrTabWidget(BaseTabWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.pandoc_installed = False
        self.temp_dir = os.path.join(os.path.expanduser("~"), ".pdfoptimizer", "temp")
        if not os.path.exists(self.temp_dir):
            os.makedirs(self.temp_dir)
            
        self._load_config()
        self.update_pandoc_status(shutil.which("pandoc") is not None)
        # 使用正确的常量
        self.start_button.setText(const.OCR_BUTTON_TEXT)

    def _setup_ui(self):
        super()._setup_ui()

        # 配置按钮
        # 使用正确的常量
        self.config_button = create_control_button(const.OCR_CONFIG_BUTTON_TEXT, self._open_ocr_config_dialog)
        self.file_select_layout.insertWidget(1, self.config_button)
        # 使用正确的常量
        self.select_button.setText(const.SELECT_SINGLE_PDF_BUTTON_TEXT)

        # 结果显示
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText(const.OCR_RESULT_PLACEHOLDER)
        self.layout().insertWidget(2, self.result_text)

        # 添加性能分析复选框
        debug_layout = QHBoxLayout()
        self.profiling_checkbox = QCheckBox(const.ENABLE_PROFILING_CHECKBOX)
        debug_layout.addWidget(self.profiling_checkbox)
        debug_layout.addStretch()
        # 将其添加到结果文本区域下方
        self.layout().insertLayout(3, debug_layout)

        self.other_controls.extend([self.config_button, self.profiling_checkbox])

    def _create_table_widget(self):
        table = super()._create_table_widget()
        table.setColumnCount(len(const.OCR_HEADERS))
        # 使用正确的常量
        table.setHorizontalHeaderLabels(const.OCR_HEADERS)
        table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        return table

    def add_files(self, files):
        if not files:
            return
        # OCR只处理单个文件
        file_path = files
        if self.file_table.rowCount() > 0:
             CustomMessageBox.information(
                self, "提示", "OCR功能一次只能处理一个文件。新文件已替换旧文件。"
            )
        self.file_table.setRowCount(1)
        item_name = QTableWidgetItem(os.path.basename(file_path))
        item_name.setData(Qt.UserRole, file_path)
        self.file_table.setItem(0, 0, item_name)
        self.file_table.setItem(0, 1, QTableWidgetItem("待处理"))

        self.main_window.status_label.setText(f"已添加文件: {os.path.basename(file_path)}")
        self._reset_ui_texts()
        self.update_controls_state()
        
    def _reset_ui_texts(self):
        self.progress_bar.setValue(0)
        self.result_text.clear()
        if self.file_table.rowCount() > 0:
            self.file_table.setItem(0, 1, QTableWidgetItem("排队中..."))

    def clear_list(self):
        super().clear_list()
        self.result_text.clear()
        self.main_window.status_label.setText("请选择一个PDF文件进行OCR")

    def stop_task(self):
        if self.worker and self.worker.isRunning():
            self.worker.stop()
            self.task_finished.emit("OCR任务已手动停止。")

    def _load_config(self):
        self.env_path = os.path.join(os.path.expanduser("~"), ".pdfoptimizer", ".env")
        if not os.path.exists(os.path.dirname(self.env_path)):
            os.makedirs(os.path.dirname(self.env_path))
        dotenv.load_dotenv(dotenv_path=self.env_path)

    def start_task(self):
        if self.file_table.rowCount() == 0:
            CustomMessageBox.warning(self, "警告", "请先选择一个PDF文件进行OCR。")
            return

        if not self.pandoc_installed:
            reply = CustomMessageBox.question(
                self,
                "依赖缺失",
                "未找到 Pandoc。无法将结果自动保存为 .docx 文件。是否继续？",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply == QMessageBox.StandardButton.No:
                return

        if os.path.exists(self.env_path):
            dotenv.load_dotenv(dotenv_path=self.env_path, override=True)

        api_provider = os.getenv("OCR_API_PROVIDER", "OpenAI-Compatible")

        if api_provider == "Mistral API":
            api_key = os.getenv("MISTRAL_API_KEY", "")
            model_name = os.getenv("MISTRAL_MODEL_NAME", "mistral-large-latest")
        else:
            api_key = os.getenv("OPENAI_API_KEY", "")
            model_name = os.getenv("OPENAI_MODEL_NAME", "gpt-4o")

        if not api_key:
            CustomMessageBox.warning(
                self, "警告", f"请在配置中设置 {api_provider} 的API密钥。"
            )
            self._open_ocr_config_dialog()
            return
            
        self._reset_ui_texts()
        self.result_text.clear()
        
        file_path_data = self.file_table.item(0, 0).data(Qt.UserRole)

        if not file_path_data:
            CustomMessageBox.warning(self, "错误", "无法获取文件路径。")
            return

        api_base_url = os.getenv("OCR_API_BASE_URL", "https://api.openai.com/v1")
        prompt_text = os.getenv("OCR_PROMPT", const.DEFAULT_OCR_PROMPT)

        self.task_started.emit()

        params = {
            "file_path": file_path_data,
            "api_key": api_key,
            "model_name": model_name,
            "api_base_url": api_base_url,
            "prompt_text": prompt_text,
            "temp_dir": self.temp_dir,
            "api_provider": api_provider,
            "enable_profiling": self.profiling_checkbox.isChecked(),
        }

        self.worker = ProcessingWorker(run_ocr_on_file, **params)
        
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.status_updated.connect(
            lambda msg: self.file_table.setItem(0, 1, QTableWidgetItem(msg))
        )
        self.worker.preview_updated.connect(self.result_text.setPlainText)
        self.worker.file_finished.connect(self.on_ocr_finished)
        self.worker.finished.connect(lambda: self.task_finished.emit("OCR任务已完成"))
        self.worker.error.connect(lambda msg: CustomMessageBox.critical(self, "错误", msg))
        
        self.worker.start()
        self.main_window.status_label.setText(f"正在使用 {api_provider} ({model_name}) 进行OCR...")


    def on_ocr_finished(self, index, result):
        logger = result.get("logger", logging.getLogger(__name__))

        if result.get("success"):
            markdown_content = result.get("markdown_content", "")
            logger.info(f"接收到OCR结果，长度: {len(markdown_content)}")

            self.result_text.setPlainText(markdown_content)
            self.file_table.setItem(0, 1, QTableWidgetItem(const.OCR_SUCCESS))

            try:
                file_path_data = self.file_table.item(0, 0).data(Qt.UserRole)
                if not file_path_data:
                    raise Exception("无法获取原始文件路径用于保存结果。")

                base_name_with_ext = os.path.basename(file_path_data)
                base_name, _ = os.path.splitext(base_name_with_ext)
                output_dir = os.path.dirname(file_path_data)

                md_filename = f"{base_name}[ocr].md"
                md_save_path = os.path.join(output_dir, md_filename)
                with open(md_save_path, "w", encoding="utf-8") as f:
                    f.write(markdown_content)
                logger.info(f"OCR结果已保存到: {md_save_path}")

                docx_save_path = None
                if self.pandoc_installed:
                    docx_filename = f"{base_name}[ocr].docx"
                    docx_save_path = os.path.join(output_dir, docx_filename)
                    processed_content = preprocess_markdown_for_pandoc(markdown_content)
                    conversion_result = convert_markdown_to_docx_with_pandoc(
                        processed_content, docx_save_path
                    )
                    if conversion_result["success"]:
                        logger.info(f"OCR结果已转换为DOCX: {docx_save_path}")
                    else:
                        logger.error(f"DOCX转换失败: {conversion_result['message']}")
                        CustomMessageBox.warning(
                            self,
                            "Word转换失败",
                            f"无法将Markdown转换为Word文档。\n错误: {conversion_result['message']}",
                        )
                        docx_save_path = None
                else:
                    logger.warning("未找到Pandoc，跳过DOCX转换。")

                if docx_save_path:
                    save_message = f"结果已保存到:\n{md_save_path}\n{docx_save_path}"
                    self.task_finished.emit(const.OCR_SUCCESS_MSG)
                else:
                    save_message = f"结果已保存到:\n{md_save_path}"
                    self.task_finished.emit(const.OCR_SUCCESS_MD_ONLY_MSG)

                CustomMessageBox.information(self, "OCR成功", save_message)

            except Exception as e:
                error_msg = f"自动保存OCR结果时出错: {str(e)}"
                logger.error(error_msg, exc_info=True)
                self.task_finished.emit(const.OCR_SAVE_FAIL_MSG)
                CustomMessageBox.warning(
                    self,
                    "自动保存失败",
                    f"OCR识别完成，但自动保存文件时遇到问题。\n错误: {error_msg}",
                )
        else:
            error_message = result.get("message", "发生未知错误")
            self.file_table.setItem(0, 1, QTableWidgetItem(const.OCR_FAIL_MSG))
            self.result_text.setText(f"发生错误:\n{error_message}")
            CustomMessageBox.warning(self, "OCR失败", f"处理失败！\n{error_message}")
            self.task_finished.emit(const.OCR_FAIL_MSG)

    def _open_ocr_config_dialog(self):
        dialog = OcrConfigDialog(self)
        dialog.exec()
        self._load_config() # 重新加载配置
        self.update_controls_state()

    def update_controls_state(self):
        super().update_controls_state()
        is_running = self._is_task_running
        self.config_button.setEnabled(not is_running)

    def update_pandoc_status(self, installed):
        """由 MainWindow 调用以更新 pandoc 状态"""
        self.pandoc_installed = installed
        self.update_controls_state()