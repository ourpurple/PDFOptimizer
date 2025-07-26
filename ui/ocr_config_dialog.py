import sys
import os

from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QFormLayout,
    QLineEdit,
    QTextEdit,
    QPushButton,
    QComboBox,
    QMessageBox,
    QApplication,
    QWidget,
)
from PySide6.QtCore import Qt, QThread, Signal
from PySide6.QtGui import QIcon
import httpx
import dotenv

# 尝试导入主窗口的资源路径函数
try:
    from .main_window import resource_path
except ImportError:
    # 如果无法导入，则定义一个简单的 resource_path 函数
    def resource_path(relative_path):
        """获取资源的绝对路径"""
        if hasattr(sys, "_MEIPASS"):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)


class FetchModelsWorker(QThread):
    """后台线程，用于获取模型列表"""

    models_fetched = Signal(list)  # 成功获取模型列表时发出信号
    error_occurred = Signal(str)  # 发生错误时发出信号

    def __init__(self, api_base_url, api_key):
        super().__init__()
        self.api_base_url = api_base_url
        self.api_key = api_key

    def run(self):
        try:
            headers = {"Authorization": f"Bearer {self.api_key}"}
            # 使用 httpx 异步客户端进行请求
            # 注意：在 QThread 中直接使用 httpx.Client() 也是可以的
            with httpx.Client() as client:
                response = client.get(
                    f"{self.api_base_url.rstrip('/')}/models",
                    headers=headers,
                    timeout=10.0,  # 10秒超时
                )
                response.raise_for_status()  # 如果状态码是 4xx 或 5xx，则引发异常

            data = response.json()
            # 根据 OpenAI API 的响应格式，模型列表在 'data' 键下
            # 并且每个模型对象有一个 'id' 键
            models = [model["id"] for model in data.get("data", []) if "id" in model]
            self.models_fetched.emit(models)

        except Exception as e:
            self.error_occurred.emit(str(e))


class OcrConfigDialog(QDialog):
    """OCR 配置对话框"""

    def __init__(self, parent=None, env_path=None):
        super().__init__(parent)
        self.env_path = env_path or os.path.join(os.path.expanduser("~"), ".pdfoptimizer", ".env")
        self.models_path = os.path.join(os.path.dirname(self.env_path), "ocr_models.txt")
        self.fetch_models_worker = None
        self.api_keys = {}  # 用于存储不同提供商的API密钥
        self.model_names = {}  # 用于存储不同提供商的模型名称
        self.previous_provider_index = 0  # 用于跟踪切换前的提供商

        self.setWindowTitle("OCR 配置")
        self.setWindowIcon(QIcon(resource_path("ui/app.ico")))  # 尝试设置图标
        self.setFixedSize(500, 400)  # 设置一个固定大小

        self._setup_ui()
        self._load_config()

        # 连接信号和槽
        self.api_provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.api_url_input.textChanged.connect(self._on_api_url_changed)
        self.api_key_input.textChanged.connect(self._on_api_key_changed)
        self.fetch_models_button.clicked.connect(self._fetch_models)
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)

    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)

        # --- 配置表单 ---
        self.form_layout = QFormLayout()

        self.api_provider_combo = QComboBox()
        self.api_provider_combo.addItems(["OpenAI-Compatible", "Mistral API"])

        self.api_url_input = QLineEdit()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)  # 隐藏密码输入

        self.model_name_combo = QComboBox()
        self.model_name_combo.setEditable(True)  # 允许用户手动输入模型名称

        self.prompt_input = QTextEdit()
        self.prompt_input.setFixedHeight(100)  # 设置提示词输入框的高度

        self.form_layout.addRow("API 提供商:", self.api_provider_combo)

        # 将 API Base URL 的标签和输入框保存为成员变量，以便隐藏/显示
        # 创建一个 QWidget 作为容器，以便更容易地隐藏和显示整行
        self.api_url_widget = QWidget()
        api_url_layout = QHBoxLayout(self.api_url_widget)
        api_url_layout.setContentsMargins(0, 0, 0, 0)
        api_url_layout.addWidget(self.api_url_input)
        self.api_url_label = self.form_layout.addRow("API Base URL:", self.api_url_widget)

        self.form_layout.addRow("API Key:", self.api_key_input)
        self.form_layout.addRow("模型名称:", self.model_name_combo)
        self.form_layout.addRow("提示词 (Prompt):", self.prompt_input)

        layout.addLayout(self.form_layout)

        # --- 模型获取按钮 ---
        self.fetch_models_button = QPushButton("获取模型列表")
        self.fetch_models_button.setToolTip("从API获取可用的模型列表")
        # 初始状态下禁用按钮，直到API URL和API Key都填写
        self.fetch_models_button.setEnabled(False)

        button_layout = QHBoxLayout()
        button_layout.addStretch()
        button_layout.addWidget(self.fetch_models_button)
        layout.addLayout(button_layout)

        # --- 分隔线 ---
        line = QWidget()
        line.setFixedHeight(1)
        line.setStyleSheet("background-color: gray;")
        layout.addWidget(line)

        # --- 对话框按钮 ---
        buttons_layout = QHBoxLayout()
        self.save_button = QPushButton("保存")
        self.cancel_button = QPushButton("取消")

        # self.save_button.clicked.connect(self.accept) # 改为在accept中直接调用save
        # self.cancel_button.clicked.connect(self.reject)

        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)

    def _load_config(self):
        """从 .env 文件加载配置"""
        if os.path.exists(os.path.dirname(self.env_path)):
            # 强制从.env文件重新加载，并覆盖已存在的环境变量
            # 这是确保对话框每次打开都显示最新配置的关键
            dotenv.load_dotenv(dotenv_path=self.env_path, override=True)

        # 1. 加载所有配置到内存
        provider = os.getenv("OCR_API_PROVIDER", "OpenAI-Compatible")
        self.api_url_input.setText(os.getenv("OCR_API_BASE_URL", "https://api.openai.com/v1"))
        self.api_keys["Mistral API"] = os.getenv("MISTRAL_API_KEY", "")
        self.api_keys["OpenAI-Compatible"] = os.getenv("OPENAI_API_KEY", "")

        # 兼容旧的 OCR_MODEL_NAME，并分别加载新的特定于提供商的模型名称
        self.model_names["Mistral API"] = os.getenv("MISTRAL_MODEL_NAME", "mistral-ocr-latest")
        # 为OpenAI兼容模式提供一个更通用的默认值，并从旧变量迁移
        self.model_names["OpenAI-Compatible"] = os.getenv(
            "OPENAI_MODEL_NAME", os.getenv("OCR_MODEL_NAME", "gpt-4o")
        )
        self.prompt_input.setPlainText(
            os.getenv(
                "OCR_PROMPT",
                "这是一个PDF页面。请准确识别所有内容，并将其转换为结构良好的Markdown格式。",
            )
        )

        # 加载保存的模型列表
        if os.path.exists(self.models_path):
            try:
                with open(self.models_path, "r", encoding="utf-8") as f:
                    models = [line.strip() for line in f.readlines() if line.strip()]
                if models:
                    current_model = self.model_name_combo.currentText()
                    self.model_name_combo.clear()
                    self.model_name_combo.addItems(models)
                    # 尝试恢复之前的选择，如果不存在则添加到列表中
                    if current_model in models:
                        self.model_name_combo.setCurrentText(current_model)
                    else:
                        self.model_name_combo.insertItem(0, current_model)
                        self.model_name_combo.setCurrentText(current_model)
            except Exception as e:
                print(f"加载模型列表失败: {e}")  # 静默处理，不打扰用户
        else:
            # 如果没有保存的模型列表，添加一些常见的模型名称作为默认选项
            common_models = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "glm-4v"]
            # 检查是否已经添加了这些模型，避免重复
            existing_items = [
                self.model_name_combo.itemText(i) for i in range(self.model_name_combo.count())
            ]
            for model in common_models:
                if model not in existing_items:
                    self.model_name_combo.addItem(model)

        # --- 初始化UI状态 ---
        # 2. 设置UI显示，同时防止加载时触发不必要的信号
        # 这是修复配置无法保存的关键：在以编程方式设置初始值时，阻止信号触发
        self.api_provider_combo.blockSignals(True)
        self.api_provider_combo.setCurrentText(provider)
        self.api_provider_combo.blockSignals(False)

        # 3. 手动初始化跟踪变量和UI状态，因为信号被阻止了
        self.previous_provider_text = provider
        self._update_ui_for_provider(provider)  # 更新UI（API Key输入框等）
        self._update_models_for_provider(provider)  # 更新模型列表

    def save_config(self):
        """保存配置到 .env 文件"""
        try:
            env_dir = os.path.dirname(self.env_path)
            if not os.path.exists(env_dir):
                os.makedirs(env_dir)

            # 在保存前，将当前输入框的API密钥更新到字典中
            current_provider = self.api_provider_combo.currentText()
            current_provider = self.api_provider_combo.currentText()
            self.api_keys[current_provider] = self.api_key_input.text()
            self.model_names[current_provider] = self.model_name_combo.currentText()

            # 保存所有配置项
            dotenv.set_key(
                self.env_path, "OCR_API_PROVIDER", self.api_provider_combo.currentText()
            )
            dotenv.set_key(self.env_path, "OCR_API_BASE_URL", self.api_url_input.text())
            # 保存提示词
            dotenv.set_key(self.env_path, "OCR_PROMPT", self.prompt_input.toPlainText())

            # 分别保存不同提供商的API密钥和模型名称
            dotenv.set_key(self.env_path, "MISTRAL_API_KEY", self.api_keys.get("Mistral API", ""))
            dotenv.set_key(
                self.env_path, "OPENAI_API_KEY", self.api_keys.get("OpenAI-Compatible", "")
            )
            dotenv.set_key(
                self.env_path,
                "MISTRAL_MODEL_NAME",
                self.model_names.get("Mistral API", "mistral-ocr-latest"),
            )
            dotenv.set_key(
                self.env_path,
                "OPENAI_MODEL_NAME",
                self.model_names.get("OpenAI-Compatible", "gpt-4o"),
            )

            # 可以考虑移除旧的 OCR_MODEL_NAME
            if os.getenv("OCR_MODEL_NAME"):
                try:
                    # 尝试从.env文件中删除旧键
                    dotenv.unset_key(self.env_path, "OCR_MODEL_NAME")
                except Exception as e:
                    print(f"无法移除旧的 OCR_MODEL_NAME 键: {e}")  # 记录错误但不影响用户

            QMessageBox.information(self, "成功", "OCR配置已成功保存。")
            return True

        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存OCR配置失败: {e}")
            return False

    def accept(self):
        """重写 accept 方法，在关闭对话框前保存配置"""
        if self.save_config():
            super().accept()
        # 如果保存失败，对话框不会关闭

    def _on_api_url_changed(self):
        """当API URL输入框内容改变时"""
        self._update_fetch_button_state()

    def _on_api_key_changed(self):
        """当API Key输入框内容改变时"""
        self._update_fetch_button_state()

    def _update_fetch_button_state(self):
        """更新获取模型按钮的状态"""
        provider = self.api_provider_combo.currentText()
        if provider == "Mistral API":
            self.fetch_models_button.setEnabled(False)
            self.fetch_models_button.setToolTip("Mistral API 不需要手动获取模型列表")
            return

        # 对于 OpenAI-Compatible provider
        url = self.api_url_input.text().strip()
        key = self.api_key_input.text().strip()
        is_enabled = bool(url and key)
        self.fetch_models_button.setEnabled(is_enabled)
        if is_enabled:
            self.fetch_models_button.setToolTip("从API获取可用的模型列表")
        else:
            self.fetch_models_button.setToolTip("请先填写 API Base URL 和 API Key")

    def _on_provider_changed(self, index):
        """当API提供商改变时，更新UI"""
        # 1. 保存切换前的API Key
        # 注意：这里需要确保 `self.previous_provider_text` 在首次运行时是有效的
        if hasattr(self, "previous_provider_text"):
            self.api_keys[self.previous_provider_text] = self.api_key_input.text()
            self.model_names[self.previous_provider_text] = self.model_name_combo.currentText()

        # 2. 更新UI
        current_provider = self.api_provider_combo.currentText()
        self._update_ui_for_provider(current_provider)
        self._update_models_for_provider(current_provider)

        # 3. 更新 previous_provider_text 以备下次切换
        self.previous_provider_text = current_provider

    def _update_ui_for_provider(self, provider):
        """根据提供商更新UI元素（API Key输入框，URL可见性等）"""
        is_mistral = provider == "Mistral API"

        # 隐藏/显示 API Base URL 行
        # 直接操作 QFormLayout 的 setRowVisible 可能更可靠
        for i in range(self.form_layout.rowCount()):
            label_item = self.form_layout.itemAt(i, QFormLayout.LabelRole)
            if label_item and label_item.widget().text() == "API Base URL:":
                self.form_layout.setRowVisible(i, not is_mistral)
                break

        # 加载新提供商的API Key
        self.api_key_input.setText(self.api_keys.get(provider, ""))

        # 更新获取按钮状态
        self._update_fetch_button_state()

    def _update_models_for_provider(self, provider):
        """根据提供商更新模型列表"""
        self.model_name_combo.clear()
        if provider == "Mistral API":
            # 添加 Mistral 的模型
            mistral_models = ["mistral-ocr-latest", "mistral-large-latest"]
            self.model_name_combo.addItems(mistral_models)
            # 恢复上次保存的 Mistral 模型
            saved_model = self.model_names.get("Mistral API", "mistral-ocr-latest")
            self.model_name_combo.setCurrentText(saved_model)
        else:  # OpenAI-Compatible
            # 加载保存的或默认的 OpenAI 模型
            # 加载保存的模型列表
            if os.path.exists(self.models_path):
                try:
                    with open(self.models_path, "r", encoding="utf-8") as f:
                        models = [line.strip() for line in f.readlines() if line.strip()]
                    if models:
                        self.model_name_combo.addItems(models)
                except Exception as e:
                    print(f"加载模型列表失败: {e}")
            else:
                common_models = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "glm-4v"]
                self.model_name_combo.addItems(common_models)

            # 恢复上次保存的 OpenAI 模型（如果存在）
            saved_model = self.model_names.get("OpenAI-Compatible", "gpt-4o")
            # 确保即使模型列表为空，也能设置当前文本
            if self.model_name_combo.findText(saved_model) == -1:
                self.model_name_combo.addItem(saved_model)
            self.model_name_combo.setCurrentText(saved_model)

    def _fetch_models(self):
        """获取模型列表"""
        api_url = self.api_url_input.text().strip()
        api_key = self.api_key_input.text().strip()

        if not api_url or not api_key:
            QMessageBox.warning(self, "警告", "请先填写API Base URL和API Key。")
            return

        # 禁用按钮并显示加载状态
        self.fetch_models_button.setEnabled(False)
        self.fetch_models_button.setText("获取中...")

        # 创建并启动后台线程
        self.fetch_models_worker = FetchModelsWorker(api_url, api_key)
        self.fetch_models_worker.models_fetched.connect(self._on_models_fetched)
        self.fetch_models_worker.error_occurred.connect(self._on_fetch_models_error)
        self.fetch_models_worker.finished.connect(self._on_fetch_finished)
        self.fetch_models_worker.start()

    def _on_models_fetched(self, models):
        """当模型列表获取成功时"""
        if models:
            # 保存当前选择的模型
            current_model = self.model_name_combo.currentText()

            # 清空并重新填充下拉框
            self.model_name_combo.clear()
            self.model_name_combo.addItems(models)

            # 尝试恢复之前的选择，如果不存在则添加到列表中
            if current_model in models:
                self.model_name_combo.setCurrentText(current_model)
            else:
                self.model_name_combo.insertItem(0, current_model)
                self.model_name_combo.setCurrentText(current_model)

            # 保存模型列表到文件
            try:
                with open(self.models_path, "w", encoding="utf-8") as f:
                    f.write("\n".join(models))
            except Exception as e:
                print(f"保存模型列表失败: {e}")  # 静默处理，不打扰用户

            QMessageBox.information(
                self,
                "成功",
                f"成功获取到 {len(models)} 个模型。\n\n可用模型列表已更新，您可以从下拉菜单中选择合适的模型。",
            )
        else:
            QMessageBox.information(self, "信息", "API返回了空的模型列表。")

    def _on_fetch_models_error(self, error_message):
        """当获取模型列表失败时"""
        QMessageBox.warning(self, "获取失败", f"无法获取模型列表: {error_message}")

    def _on_fetch_finished(self):
        """当后台线程结束时"""
        # 重新启用按钮并恢复文本
        self.fetch_models_button.setText("获取模型列表")
        self._update_fetch_button_state()  # 根据当前输入决定按钮是否可用
        self.fetch_models_worker = None  # 释放线程引用


# 用于测试对话框的主函数
if __name__ == "__main__":
    app = QApplication(sys.argv)

    # 创建并显示对话框
    dialog = OcrConfigDialog()
    if dialog.exec() == QDialog.DialogCode.Accepted:
        print("配置已保存")
    else:
        print("用户取消了操作")

    sys.exit(app.exec())
