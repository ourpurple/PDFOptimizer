"""
配置管理对话框
提供配置的增删改查、导入导出、测试连接等功能
"""

import os
import json
from typing import Optional, List
from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QGridLayout, QFormLayout,
    QLabel, QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QTextEdit,
    QPushButton, QTableWidget, QTableWidgetItem, QHeaderView,
    QGroupBox, QTabWidget, QMessageBox, QFileDialog, QSplitter,
    QFrame, QCheckBox, QProgressBar, QDialogButtonBox, QWidget
)
from PySide6.QtCore import Qt, QThread, Signal, QTimer
from PySide6.QtGui import QIcon, QFont
import httpx

from core.config_models import APIConfig, ConfigProfile, ValidationResult, TestResult
from core.config_manager import ConfigManager


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

class ConnectionTestThread(QThread):
    """连接测试线程"""
    result_ready = Signal(object)
    
    def __init__(self, config_manager: ConfigManager, config: APIConfig):
        super().__init__()
        self.config_manager = config_manager
        self.config = config
    
    def run(self):
        result = self.config_manager.test_connection(self.config)
        self.result_ready.emit(result)

class ConfigManagerDialog(QDialog):
    """配置管理主对话框"""
    
    config_changed = Signal()
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("OCR API配置管理")
        self.setObjectName("ConfigManagerDialog")  # 设置对象名称以便样式应用
        self.setMinimumSize(900, 600)
        self.setWindowIcon(QIcon("ui/app.ico"))
        
        self.config_manager = ConfigManager()
        self.current_config = None
        self.test_thread = None
        
        self._init_ui()
        self._load_configs()
        # 自动选择并加载默认配置
        self._select_default_config()
    
    def _init_ui(self):
        """初始化UI"""
        layout = QVBoxLayout()
        
        # 创建分割器
        splitter = QSplitter(Qt.Horizontal)
        
        # 左侧配置列表
        self._create_config_list(splitter)
        
        # 右侧配置编辑
        self._create_config_editor(splitter)
        
        # 设置分割器比例
        splitter.setSizes([300, 600])
        layout.addWidget(splitter)
        
        # 底部按钮
        self._create_bottom_buttons(layout)
        
        self.setLayout(layout)
    
    def _create_config_list(self, parent):
        """创建配置列表"""
        left_widget = QFrame()
        left_layout = QVBoxLayout()
        
        # 标题和工具按钮
        header_layout = QHBoxLayout()
        header_label = QLabel("配置列表")
        header_label.setFont(QFont("", 10, QFont.Bold))
        header_layout.addWidget(header_label)
        
        header_layout.addStretch()
        
        self.add_btn = QPushButton("新增")
        self.add_btn.clicked.connect(self._add_config)
        header_layout.addWidget(self.add_btn)
        
        self.import_btn = QPushButton("导入")
        self.import_btn.clicked.connect(self._import_configs)
        header_layout.addWidget(self.import_btn)
        
        self.export_btn = QPushButton("导出")
        self.export_btn.clicked.connect(self._export_configs)
        header_layout.addWidget(self.export_btn)
        
        left_layout.addLayout(header_layout)
        
        # 配置列表表格
        self.config_table = QTableWidget()
        self.config_table.setColumnCount(3)
        self.config_table.setHorizontalHeaderLabels(["名称", "类型", "默认"])
        self.config_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.config_table.setSelectionMode(QTableWidget.SingleSelection)
        self.config_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.config_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.config_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.config_table.itemSelectionChanged.connect(self._on_config_selected)
        self.config_table.itemDoubleClicked.connect(self._edit_config)
        
        left_layout.addWidget(self.config_table)
        
        # 快速操作按钮
        quick_layout = QHBoxLayout()
        
        self.set_default_btn = QPushButton("设为默认")
        self.set_default_btn.clicked.connect(self._set_default_config)
        self.set_default_btn.setEnabled(False)
        quick_layout.addWidget(self.set_default_btn)
        
        self.delete_btn = QPushButton("删除")
        self.delete_btn.clicked.connect(self._delete_config)
        self.delete_btn.setEnabled(False)
        quick_layout.addWidget(self.delete_btn)
        
        self.test_btn = QPushButton("测试连接")
        self.test_btn.clicked.connect(self._test_connection)
        self.test_btn.setEnabled(False)
        quick_layout.addWidget(self.test_btn)
        
        left_layout.addLayout(quick_layout)
        
        left_widget.setLayout(left_layout)
        parent.addWidget(left_widget)
    
    def _create_config_editor(self, parent):
        """创建配置编辑器"""
        right_widget = QFrame()
        right_layout = QVBoxLayout()
        
        # 标题
        title_label = QLabel("配置编辑")
        title_label.setFont(QFont("", 10, QFont.Bold))
        right_layout.addWidget(title_label)
        
        # 配置表单
        form_widget = QWidget()
        form_layout = QFormLayout(form_widget)
        
        # 配置名称
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("输入配置名称")
        form_layout.addRow("配置名称:", self.name_edit)
        
        # API提供商
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI-Compatible", "Mistral API"])
        self.provider_combo.currentTextChanged.connect(self._on_provider_changed)
        form_layout.addRow("API提供商:", self.provider_combo)
        
        # API密钥
        self.api_key_edit = QLineEdit()
        self.api_key_edit.setEchoMode(QLineEdit.Password)
        self.api_key_edit.setPlaceholderText("输入API密钥")
        form_layout.addRow("API密钥:", self.api_key_edit)
        
        # API基础URL
        self.api_base_edit = QLineEdit()
        self.api_base_edit.setPlaceholderText("输入API基础URL")
        form_layout.addRow("API基础URL:", self.api_base_edit)
        
        # 模型名称
        self.model_edit = QLineEdit()
        self.model_edit.setPlaceholderText("输入模型名称")
        form_layout.addRow("模型名称:", self.model_edit)
        
        # 温度参数
        self.temp_spin = QDoubleSpinBox()
        self.temp_spin.setRange(0.0, 2.0)
        self.temp_spin.setSingleStep(0.1)
        self.temp_spin.setValue(1.0)
        form_layout.addRow("温度:", self.temp_spin)
        
        # 保存模式
        self.save_mode_combo = QComboBox()
        self.save_mode_combo.addItems(["all_pages", "per_page"])
        form_layout.addRow("保存模式:", self.save_mode_combo)
        
        # 添加获取模型按钮
        fetch_models_layout = QHBoxLayout()
        fetch_models_layout.addStretch()
        self.fetch_models_btn = QPushButton("获取模型列表")
        self.fetch_models_btn.clicked.connect(self._fetch_models)
        fetch_models_layout.addWidget(self.fetch_models_btn)
        form_layout.addRow("", fetch_models_layout)
        
        # 添加后台线程实例变量
        self.fetch_models_worker = None
        
        # OCR提示词
        self.prompt_edit = QTextEdit()
        self.prompt_edit.setMaximumHeight(100)
        self.prompt_edit.setPlaceholderText("输入OCR提示词")
        form_layout.addRow("OCR提示词:", self.prompt_edit)
        
        # 设为默认
        self.is_default_check = QCheckBox("设为默认配置")
        form_layout.addRow("", self.is_default_check)
        
        right_layout.addWidget(form_widget)
        
        # 测试结果区域
        test_group = QGroupBox("连接测试")
        test_layout = QVBoxLayout()
        
        self.test_progress = QProgressBar()
        self.test_progress.setVisible(False)
        test_layout.addWidget(self.test_progress)
        
        self.test_result_label = QLabel("点击\"测试连接\"按钮测试API配置")
        self.test_result_label.setWordWrap(True)
        test_layout.addWidget(self.test_result_label)
        
        test_group.setLayout(test_layout)
        right_layout.addWidget(test_group)
        
        right_layout.addStretch()
        
        right_widget.setLayout(right_layout)
        parent.addWidget(right_widget)
    
    def _create_bottom_buttons(self, layout):
        """创建底部按钮"""
        button_layout = QHBoxLayout()
        
        button_layout.addStretch()
        
        self.save_btn = QPushButton("保存配置")
        self.save_btn.clicked.connect(self._save_config)
        self.save_btn.setEnabled(False)
        button_layout.addWidget(self.save_btn)
        
        self.cancel_btn = QPushButton("取消")
        self.cancel_btn.clicked.connect(self._cancel_edit)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
    
    def _load_configs(self):
        """加载配置列表"""
        profile = self.config_manager.load_configs()
        
        self.config_table.setRowCount(len(profile.configs))
        
        for row, config in enumerate(profile.configs):
            # 名称
            name_item = QTableWidgetItem(config.name)
            self.config_table.setItem(row, 0, name_item)
            
            # 提供商
            provider_item = QTableWidgetItem(config.provider)
            self.config_table.setItem(row, 1, provider_item)
            
            # 默认标记
            default_item = QTableWidgetItem("是" if config.is_default else "否")
            self.config_table.setItem(row, 2, default_item)
            
            # 存储配置ID
            name_item.setData(Qt.UserRole, config.id)
        
        # 如果有默认配置，自动选中
        default_config = profile.get_default_config()
        if default_config:
            for row in range(self.config_table.rowCount()):
                item = self.config_table.item(row, 0)
                if item and item.data(Qt.UserRole) == default_config.id:
                    self.config_table.selectRow(row)
                    break
    
    def _select_default_config(self):
        """选择并加载默认配置"""
        profile = self.config_manager.load_configs()
        default_config = profile.get_default_config()
        
        if default_config:
            # 在表格中找到默认配置并选中
            for row in range(self.config_table.rowCount()):
                item = self.config_table.item(row, 0)
                if item and item.data(Qt.UserRole) == default_config.id:
                    self.config_table.selectRow(row)
                    
                    # 触发配置选择事件以加载配置到编辑器
                    self._on_config_selected()
                    break
        else:
            # 如果没有默认配置，可以选择第一个配置或保持空白
            if self.config_table.rowCount() > 0:
                self.config_table.selectRow(0)
                self._on_config_selected()
    
    def _on_config_selected(self):
        """配置选择事件"""
        selected_items = self.config_table.selectedItems()
        if not selected_items:
            self._clear_editor()
            self.set_default_btn.setEnabled(False)
            self.delete_btn.setEnabled(False)
            self.test_btn.setEnabled(False)
            return
        
        row = selected_items[0].row()
        config_id = self.config_table.item(row, 0).data(Qt.UserRole)
        
        profile = self.config_manager.load_configs()
        config = profile.get_config(config_id)
        
        if config:
            self._load_config_to_editor(config)
            self.set_default_btn.setEnabled(not config.is_default)
            self.delete_btn.setEnabled(True)
            self.test_btn.setEnabled(True)
            self.save_btn.setEnabled(True)
            # 更新获取模型按钮状态
            self._update_fetch_button_state()
    
    def _load_config_to_editor(self, config: APIConfig):
        """加载配置到编辑器"""
        self.current_config = config
        
        self.name_edit.setText(config.name or "")
        self.provider_combo.setCurrentText(config.provider or "")
        self.api_key_edit.setText(config.api_key or "")
        self.api_base_edit.setText(config.api_base_url or "")
        self.model_edit.setText(config.model_name or "")
        self.temp_spin.setValue(config.temperature or 1.0)
        self.save_mode_combo.setCurrentText(config.save_mode or "per_page")
        self.prompt_edit.setPlainText(config.prompt or "")
        self.is_default_check.setChecked(config.is_default or False)
        
        self._on_provider_changed(config.provider)
        # 更新获取模型按钮状态
        self._update_fetch_button_state()
    
    def _clear_editor(self):
        """清空编辑器"""
        self.current_config = None
        
        self.name_edit.clear()
        self.provider_combo.setCurrentIndex(0)
        self.api_key_edit.clear()
        self.api_base_edit.clear()
        self.model_edit.clear()
        self.temp_spin.setValue(1.0)
        self.save_mode_combo.setCurrentIndex(0)
        self.prompt_edit.clear()
        self.is_default_check.setChecked(False)
        
        self.test_result_label.setText("点击\"测试连接\"按钮测试API配置")
    
    def _on_provider_changed(self, provider: str):
        """提供商改变事件"""
        if provider == "Mistral API":
            # 只在当前API基础URL为空或为默认值时设置
            if not self.api_base_edit.text() or self.api_base_edit.text() == "https://api.openai.com/v1":
                self.api_base_edit.setText("https://api.mistral.ai/v1")
            self.api_base_edit.setEnabled(False)
            # 只在当前模型名称为空或为默认值时设置
            if not self.model_edit.text() or self.model_edit.text() == "gpt-4o":
                self.model_edit.setText("mistral-ocr-latest")
            # 为Mistral API禁用获取模型按钮，因为Mistral API有固定的模型
            self.fetch_models_btn.setEnabled(False)
        else:  # OpenAI-Compatible
            # 只在当前API基础URL为空或为默认值时设置
            if not self.api_base_edit.text() or self.api_base_edit.text() == "https://api.mistral.ai/v1":
                self.api_base_edit.setText("https://api.openai.com/v1")
            self.api_base_edit.setEnabled(True)
            # 只在当前模型名称为空或为默认值时设置
            if not self.model_edit.text() or self.model_edit.text() == "mistral-ocr-latest":
                self.model_edit.setText("gpt-4o")
            # 为OpenAI兼容模式启用获取模型按钮
            self.fetch_models_btn.setEnabled(True)
    
    def _update_fetch_button_state(self):
        """更新获取模型按钮状态"""
        provider = self.provider_combo.currentText()
        if provider == "Mistral API":
            self.fetch_models_btn.setEnabled(False)
        else:  # OpenAI-Compatible
            self.fetch_models_btn.setEnabled(True)
            
    def _fetch_models(self):
        """获取模型列表"""
        api_base_url = self.api_base_edit.text().strip()
        api_key = self.api_key_edit.text().strip()
        
        if not api_base_url or not api_key:
            QMessageBox.warning(self, "警告", "请先输入API基础URL和API密钥")
            return
            
        # 启动后台线程获取模型列表
        self.fetch_models_worker = FetchModelsWorker(api_base_url, api_key)
        self.fetch_models_worker.models_fetched.connect(self._on_models_fetched)
        self.fetch_models_worker.error_occurred.connect(self._on_fetch_error)
        
        # 禁用按钮和编辑器，防止重复点击
        self.fetch_models_btn.setEnabled(False)
        self.fetch_models_btn.setText("获取中...")
        
        self.fetch_models_worker.start()
    
    def _on_models_fetched(self, models):
        """模型列表获取成功回调"""
        # 恢复按钮状态
        self.fetch_models_btn.setEnabled(True)
        self.fetch_models_btn.setText("获取模型列表")
            
        if models:
            # 显示模型选择对话框
            from PySide6.QtWidgets import QInputDialog
            model, ok = QInputDialog.getItem(
                self, "选择模型", "请选择一个模型:", models, 0, False
            )
            
            if ok and model:
                self.model_edit.setText(model)
                
        else:
            QMessageBox.information(self, "提示", "未找到可用模型或API响应格式不正确")
            
    def _on_fetch_error(self, error_msg):
        """模型列表获取失败回调"""
        QMessageBox.critical(self, "错误", f"获取模型列表失败: {error_msg}")
            
        # 恢复按钮状态
        self.fetch_models_btn.setEnabled(True)
        self.fetch_models_btn.setText("获取模型列表")
    
    def _add_config(self):
        """添加新配置"""
        self._clear_editor()
        self.name_edit.setFocus()
        self.save_btn.setEnabled(True)
        self.config_table.clearSelection()
    
    def _edit_config(self, item):
        """编辑配置"""
        self._on_config_selected()
    
    def _save_config(self):
        """保存配置"""
        # 验证输入
        name = self.name_edit.text().strip()
        if not name:
            QMessageBox.warning(self, "错误", "请输入配置名称")
            return
        
        api_key = self.api_key_edit.text().strip()
        if not api_key:
            QMessageBox.warning(self, "错误", "请输入API密钥")
            return
            
        api_base_url = self.api_base_edit.text().strip()
        if not api_base_url:
            QMessageBox.warning(self, "错误", "请输入API基础URL")
            return
            
        model_name = self.model_edit.text().strip()
        if not model_name:
            QMessageBox.warning(self, "错误", "请输入模型名称或使用获取模型功能")
            return
        
        # 创建配置对象
        config = APIConfig(
            name=name,
            provider=self.provider_combo.currentText(),
            api_key=api_key,
            api_base_url=api_base_url,
            model_name=model_name,
            temperature=self.temp_spin.value(),
            save_mode=self.save_mode_combo.currentText(),
            prompt=self.prompt_edit.toPlainText().strip(),
            is_default=self.is_default_check.isChecked()
        )
        
        # 验证配置
        validation = self.config_manager.validate_config(config)
        if not validation.is_valid:
            QMessageBox.warning(self, "配置验证失败", "\n".join(validation.errors))
            return
        
        # 更新获取模型按钮状态
        self._update_fetch_button_state()
        
        # 保存配置
        profile = self.config_manager.load_configs()
        
        if self.current_config:
            # 更新现有配置 - 确保ID正确设置
            config.id = self.current_config.id
            config.created_at = self.current_config.created_at  # 保留原始创建时间
            profile.update_config(self.current_config.id, config)
        else:
            # 添加新配置 - 让APIConfig生成新的ID
            if self.is_default_check.isChecked():
                profile.clear_default()
            profile.add_config(config)
        
        # 保存配置文件
        if self.config_manager.save_configs(profile):
            self._load_configs()
            self.config_changed.emit()
            QMessageBox.information(self, "成功", "配置保存成功")
            
            # 更新获取模型按钮状态
            self._update_fetch_button_state()
        else:
            QMessageBox.critical(self, "错误", "配置保存失败")
            
            # 更新获取模型按钮状态
            self._update_fetch_button_state()
    
    def _cancel_edit(self):
        """取消编辑"""
        self._load_configs()
        self._clear_editor()
        # 更新获取模型按钮状态
        self._update_fetch_button_state()
    
    def _delete_config(self):
        """删除配置"""
        selected_items = self.config_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        config_id = self.config_table.item(row, 0).data(Qt.UserRole)
        config_name = self.config_table.item(row, 0).text()
        
        reply = QMessageBox.question(
            self, "确认删除",
            f"确定要删除配置\"{config_name}\"吗？\n\n此操作不可撤销。",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            profile = self.config_manager.load_configs()
            if profile.remove_config(config_id):
                if self.config_manager.save_configs(profile):
                    self._load_configs()
                    self._clear_editor()
                    self.config_changed.emit()
                    QMessageBox.information(self, "成功", "配置删除成功")
                else:
                    QMessageBox.critical(self, "错误", "配置删除失败")
                
                # 更新获取模型按钮状态
                self._update_fetch_button_state()
    
    def _set_default_config(self):
        """设置默认配置"""
        selected_items = self.config_table.selectedItems()
        if not selected_items:
            return
        
        row = selected_items[0].row()
        config_id = self.config_table.item(row, 0).data(Qt.UserRole)
        
        profile = self.config_manager.load_configs()
        if profile.set_default_config(config_id):
            if self.config_manager.save_configs(profile):
                self._load_configs()
                self.config_changed.emit()
                QMessageBox.information(self, "成功", "默认配置设置成功")
            else:
                QMessageBox.critical(self, "错误", "默认配置设置失败")
            
            # 更新获取模型按钮状态
            self._update_fetch_button_state()
    
    def _test_connection(self):
        """测试连接"""
        # 获取当前编辑的配置（不依赖当前配置对象，直接从界面获取最新值）
        config = APIConfig(
            name=self.name_edit.text().strip() or "Test Config",
            provider=self.provider_combo.currentText(),
            api_key=self.api_key_edit.text().strip(),
            api_base_url=self.api_base_edit.text().strip(),
            model_name=self.model_edit.text().strip(),
            temperature=self.temp_spin.value(),
            save_mode=self.save_mode_combo.currentText(),
            prompt=self.prompt_edit.toPlainText().strip(),
            is_default=self.is_default_check.isChecked()
        )
        
        # 如果当前正在编辑已有配置，保留其ID
        if self.current_config:
            config.id = self.current_config.id
        
        # 验证配置
        validation = self.config_manager.validate_config(config)
        if not validation.is_valid:
            QMessageBox.warning(self, "配置验证失败", "\n".join(validation.errors))
            return
        
        # 更新获取模型按钮状态
        self._update_fetch_button_state()
        
        # 开始测试
        self.test_progress.setVisible(True)
        self.test_progress.setRange(0, 0)  # 无限进度条
        self.test_result_label.setText("正在测试连接...")
        self.test_btn.setEnabled(False)
        
        # 启动测试线程
        self.test_thread = ConnectionTestThread(self.config_manager, config)
        self.test_thread.result_ready.connect(self._on_test_result)
        self.test_thread.start()
    
    def _on_test_result(self, result: TestResult):
        """测试结果回调"""
        self.test_progress.setVisible(False)
        self.test_btn.setEnabled(True)
        
        if result.success:
            self.test_result_label.setText(
                f"✅ {result.message}\n"
                f"响应时间: {result.response_time:.2f}秒"
            )
            if result.details:
                self.test_result_label.setText(
                    self.test_result_label.text() + 
                    f"\n详细信息: {result.details}"
                )
        else:
            self.test_result_label.setText(
                f"❌ {result.message}\n"
                f"响应时间: {result.response_time:.2f}秒"
            )
    
    def _import_configs(self):
        """导入配置"""
        file_path, _ = QFileDialog.getOpenFileName(
            self, "导入配置", "", "JSON文件 (*.json)"
        )
        
        if file_path:
            reply = QMessageBox.question(
                self, "导入选项",
                "是否合并导入的配置？\n\n"
                "• 是：将导入的配置添加到现有配置中\n"
                "• 否：用导入的配置替换现有配置",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Cancel:
                return
            
            merge = (reply == QMessageBox.Yes)
            imported_configs = self.config_manager.import_configs(file_path, merge)
            
            if imported_configs:
                self._load_configs()
                self.config_changed.emit()
                QMessageBox.information(
                    self, "导入成功",
                    f"成功导入 {len(imported_configs)} 个配置"
                )
            else:
                QMessageBox.critical(self, "导入失败", "无法导入配置文件")
            
            # 更新获取模型按钮状态
            self._update_fetch_button_state()
    
    def _export_configs(self):
        """导出配置"""
        file_path, _ = QFileDialog.getSaveFileName(
            self, "导出配置", "ocr_configs.json", "JSON文件 (*.json)"
        )
        
        if file_path:
            if self.config_manager.export_configs(file_path):
                QMessageBox.information(self, "导出成功", "配置导出成功")
            else:
                QMessageBox.critical(self, "导出失败", "无法导出配置文件")
            
            # 更新获取模型按钮状态
            self._update_fetch_button_state()