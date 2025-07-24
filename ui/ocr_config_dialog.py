import sys
import os

from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QFormLayout, QLineEdit, QTextEdit,
    QPushButton, QComboBox, QMessageBox, QApplication, QWidget
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
        if hasattr(sys, '_MEIPASS'):
            return os.path.join(sys._MEIPASS, relative_path)
        return os.path.join(os.path.abspath("."), relative_path)

class FetchModelsWorker(QThread):
    """后台线程，用于获取模型列表"""
    models_fetched = Signal(list)  # 成功获取模型列表时发出信号
    error_occurred = Signal(str)   # 发生错误时发出信号

    def __init__(self, api_base_url, api_key):
        super().__init__()
        self.api_base_url = api_base_url
        self.api_key = api_key

    def run(self):
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}"
            }
            # 使用 httpx 异步客户端进行请求
            # 注意：在 QThread 中直接使用 httpx.Client() 也是可以的
            with httpx.Client() as client:
                response = client.get(
                    f"{self.api_base_url.rstrip('/')}/models",
                    headers=headers,
                    timeout=10.0  # 10秒超时
                )
                response.raise_for_status()  # 如果状态码是 4xx 或 5xx，则引发异常
            
            data = response.json()
            # 根据 OpenAI API 的响应格式，模型列表在 'data' 键下
            # 并且每个模型对象有一个 'id' 键
            models = [model['id'] for model in data.get('data', []) if 'id' in model]
            self.models_fetched.emit(models)
            
        except Exception as e:
            self.error_occurred.emit(str(e))


class OcrConfigDialog(QDialog):
    """OCR 配置对话框"""
    
    def __init__(self, parent=None, env_path=None):
        super().__init__(parent)
        self.env_path = env_path or os.path.join(os.path.expanduser("~"), ".pdfoptimizer", ".env")
        self.models_path = os.path.join(os.path.dirname(self.env_path), "ocr_models.txt")
        self.fetch_models_worker = None  # 用于获取模型列表的后台线程
        
        self.setWindowTitle("OCR 配置")
        self.setWindowIcon(QIcon(resource_path("ui/app.ico"))) # 尝试设置图标
        self.setFixedSize(500, 400)  # 设置一个固定大小
        
        self._setup_ui()
        self._load_config()
        
        # 连接信号和槽
        self.api_url_input.textChanged.connect(self._on_api_url_changed)
        self.api_key_input.textChanged.connect(self._on_api_key_changed)
        self.fetch_models_button.clicked.connect(self._fetch_models)
        
    def _setup_ui(self):
        """设置UI布局"""
        layout = QVBoxLayout(self)
        
        # --- 配置表单 ---
        form_layout = QFormLayout()
        
        self.api_url_input = QLineEdit()
        self.api_key_input = QLineEdit()
        self.api_key_input.setEchoMode(QLineEdit.EchoMode.Password)  # 隐藏密码输入
        
        self.model_name_combo = QComboBox()
        self.model_name_combo.setEditable(True)  # 允许用户手动输入模型名称
        # 添加一些常见的模型名称作为默认选项
        common_models = ["gpt-4o", "gpt-4o-mini", "claude-3-5-sonnet", "glm-4v"]
        self.model_name_combo.addItems(common_models)
        
        self.prompt_input = QTextEdit()
        self.prompt_input.setFixedHeight(100)  # 设置提示词输入框的高度
        
        form_layout.addRow("API Base URL:", self.api_url_input)
        form_layout.addRow("API Key:", self.api_key_input)
        form_layout.addRow("模型名称:", self.model_name_combo)
        form_layout.addRow("提示词 (Prompt):", self.prompt_input)
        
        layout.addLayout(form_layout)
        
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
        
        self.save_button.clicked.connect(self.accept)
        self.cancel_button.clicked.connect(self.reject)
        
        buttons_layout.addStretch()
        buttons_layout.addWidget(self.save_button)
        buttons_layout.addWidget(self.cancel_button)
        layout.addLayout(buttons_layout)
        
    def _load_config(self):
        """从 .env 文件加载配置"""
        if os.path.exists(os.path.dirname(self.env_path)):
            dotenv.load_dotenv(dotenv_path=self.env_path)
            
        self.api_url_input.setText(os.getenv("OCR_API_BASE_URL", "https://api.openai.com/v1"))
        self.api_key_input.setText(os.getenv("OCR_API_KEY", ""))
        self.model_name_combo.setCurrentText(os.getenv("OCR_MODEL_NAME", "gpt-4o"))
        self.prompt_input.setPlainText(os.getenv("OCR_PROMPT", "这是一个PDF页面。请准确识别所有内容，并将其转换为结构良好的Markdown格式。"))
        
        # 加载保存的模型列表
        if os.path.exists(self.models_path):
            try:
                with open(self.models_path, 'r', encoding='utf-8') as f:
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
            existing_items = [self.model_name_combo.itemText(i) for i in range(self.model_name_combo.count())]
            for model in common_models:
                if model not in existing_items:
                    self.model_name_combo.addItem(model)
        
        # 更新获取模型按钮的状态
        self._update_fetch_button_state()
        
    def save_config(self):
        """保存配置到 .env 文件"""
        try:
            env_dir = os.path.dirname(self.env_path)
            if not os.path.exists(env_dir):
                os.makedirs(env_dir)
                
            dotenv.set_key(self.env_path, "OCR_API_BASE_URL", self.api_url_input.text())
            dotenv.set_key(self.env_path, "OCR_API_KEY", self.api_key_input.text())
            dotenv.set_key(self.env_path, "OCR_MODEL_NAME", self.model_name_combo.currentText())
            dotenv.set_key(self.env_path, "OCR_PROMPT", self.prompt_input.toPlainText())
            
            # QMessageBox.information(self, "成功", "OCR配置已成功保存。")
            return True
        except Exception as e:
            QMessageBox.warning(self, "保存失败", f"保存OCR配置失败: {e}")
            return False
            
    def accept(self):
        """重写 accept 方法，在关闭对话框前保存配置"""
        if self.save_config():
            super().accept()
            
    def _on_api_url_changed(self):
        """当API URL输入框内容改变时"""
        self._update_fetch_button_state()
        
    def _on_api_key_changed(self):
        """当API Key输入框内容改变时"""
        self._update_fetch_button_state()
        
    def _update_fetch_button_state(self):
        """更新获取模型按钮的状态"""
        url = self.api_url_input.text().strip()
        key = self.api_key_input.text().strip()
        # 只有当API URL和API Key都不为空时才启用按钮
        self.fetch_models_button.setEnabled(bool(url and key))
        
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
                with open(self.models_path, 'w', encoding='utf-8') as f:
                    f.write('\n'.join(models))
            except Exception as e:
                print(f"保存模型列表失败: {e}")  # 静默处理，不打扰用户
                
            QMessageBox.information(self, "成功", f"成功获取到 {len(models)} 个模型。\n\n可用模型列表已更新，您可以从下拉菜单中选择合适的模型。")
        else:
            QMessageBox.information(self, "信息", "API返回了空的模型列表。")
            
    def _on_fetch_models_error(self, error_message):
        """当获取模型列表失败时"""
        QMessageBox.warning(self, "获取失败", f"无法获取模型列表: {error_message}")
        
    def _on_fetch_finished(self):
        """当后台线程结束时"""
        # 重新启用按钮并恢复文本
        self.fetch_models_button.setEnabled(True)
        self.fetch_models_button.setText("获取模型列表")
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