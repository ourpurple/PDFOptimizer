"""
配置数据模型
定义API配置的数据结构和验证逻辑
"""

from dataclasses import dataclass, field
from datetime import datetime
from typing import Dict, Any, Optional, List
import uuid
import re

@dataclass
class ValidationResult:
    """配置验证结果"""
    is_valid: bool
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)

@dataclass
class TestResult:
    """API连接测试结果"""
    success: bool
    message: str
    response_time: Optional[float] = None
    details: Dict[str, Any] = field(default_factory=dict)

@dataclass
class APIConfig:
    """单个API配置的数据模型"""
    id: str = field(default_factory=lambda: str(uuid.uuid4()))
    name: str = ""  # 配置名称（用户自定义）
    provider: str = ""  # 提供商类型（OpenAI-Compatible, Mistral等）
    api_key: str = ""  # API密钥
    api_base_url: str = ""  # API基础URL
    model_name: str = ""  # 模型名称
    temperature: float = 1.0  # 温度参数
    prompt: str = ""  # 提示词
    save_mode: str = "per_page"  # 保存模式
    is_default: bool = False  # 是否为默认配置
    created_at: datetime = field(default_factory=datetime.now)
    updated_at: datetime = field(default_factory=datetime.now)
    extra_params: Dict[str, Any] = field(default_factory=dict)  # 额外参数
    
    def __post_init__(self):
        """初始化后处理"""
        if not self.name:
            self.name = f"{self.provider} 配置"
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "id": self.id,
            "name": self.name,
            "provider": self.provider,
            "api_key": self.api_key,
            "api_base_url": self.api_base_url,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "prompt": self.prompt,
            "save_mode": self.save_mode,
            "is_default": self.is_default,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "extra_params": self.extra_params
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'APIConfig':
        """从字典创建实例"""
        config = cls()
        config.id = data.get("id", config.id)
        config.name = data.get("name", config.name)
        config.provider = data.get("provider", config.provider)
        config.api_key = data.get("api_key", config.api_key)
        config.api_base_url = data.get("api_base_url", config.api_base_url)
        config.model_name = data.get("model_name", config.model_name)
        config.temperature = data.get("temperature", config.temperature)
        config.prompt = data.get("prompt", config.prompt)
        config.save_mode = data.get("save_mode", config.save_mode)
        config.is_default = data.get("is_default", config.is_default)
        config.extra_params = data.get("extra_params", config.extra_params)
        
        # 处理时间字段
        if "created_at" in data:
            try:
                config.created_at = datetime.fromisoformat(data["created_at"])
            except (ValueError, TypeError):
                pass
        if "updated_at" in data:
            try:
                config.updated_at = datetime.fromisoformat(data["updated_at"])
            except (ValueError, TypeError):
                pass
            
        return config
    
    def validate(self) -> ValidationResult:
        """验证配置的有效性"""
        errors = []
        warnings = []
        
        if not self.name.strip():
            errors.append("配置名称不能为空")
        
        if not self.provider.strip():
            errors.append("API提供商不能为空")
        elif self.provider not in ["OpenAI-Compatible", "Mistral API"]:
            warnings.append(f"未知的API提供商: {self.provider}")
        
        if not self.api_key.strip():
            errors.append("API密钥不能为空")
        
        if self.provider == "OpenAI-Compatible" and not self.api_base_url.strip():
            errors.append("OpenAI兼容API需要提供Base URL")
        
        if not self.model_name.strip():
            errors.append("模型名称不能为空")
        
        if not 0.0 <= self.temperature <= 2.0:
            warnings.append("温度参数应在0.0-2.0范围内")
        
        if self.save_mode not in ["per_page", "merged"]:
            warnings.append("保存模式应为'per_page'或'merged'")
        
        # 验证API Key格式
        if self.provider == "OpenAI-Compatible" and self.api_key:
            if not self.api_key.startswith("sk-"):
                warnings.append("OpenAI API Key通常以'sk-'开头")
        elif self.provider == "Mistral API" and self.api_key:
            # Mistral API Key格式检查
            if len(self.api_key) < 20:
                warnings.append("Mistral API Key长度似乎不正确")
        
        return ValidationResult(
            is_valid=len(errors) == 0,
            errors=errors,
            warnings=warnings
        )
    
    def update_timestamp(self):
        """更新时间戳"""
        self.updated_at = datetime.now()

@dataclass
class ConfigProfile:
    """配置集合管理类"""
    configs: List[APIConfig] = field(default_factory=list)
    active_config_id: Optional[str] = None
    default_config_id: Optional[str] = None
    version: str = "1.0"
    
    def add_config(self, config: APIConfig) -> bool:
        """添加配置"""
        # 检查名称是否重复
        if any(c.name == config.name for c in self.configs):
            return False
        
        # 如果设置为默认，清除其他默认配置
        if config.is_default:
            for c in self.configs:
                c.is_default = False
            self.default_config_id = config.id
        
        # 如果是第一个配置，设置为激活和默认
        if not self.configs:
            config.is_default = True
            self.active_config_id = config.id
            self.default_config_id = config.id
        
        self.configs.append(config)
        return True
    
    def remove_config(self, config_id: str) -> bool:
        """删除配置"""
        config = self.get_config(config_id)
        if not config:
            return False
        
        self.configs.remove(config)
        
        # 如果删除的是激活配置，切换到默认配置
        if self.active_config_id == config_id:
            if self.default_config_id != config_id and self.get_config(self.default_config_id):
                self.active_config_id = self.default_config_id
            elif self.configs:
                self.active_config_id = self.configs[0].id
            else:
                self.active_config_id = None
        
        # 如果删除的是默认配置，设置新的默认配置
        if self.default_config_id == config_id:
            if self.configs:
                self.configs[0].is_default = True
                self.default_config_id = self.configs[0].id
            else:
                self.default_config_id = None
        
        return True
    
    def update_config(self, config_id: str, config: APIConfig) -> bool:
        """更新配置"""
        old_config = self.get_config(config_id)
        if not old_config:
            return False
        
        # 保持ID不变
        config.id = config_id
        config.update_timestamp()
        
        # 如果设置为默认，清除其他默认配置
        if config.is_default:
            for c in self.configs:
                c.is_default = False
            self.default_config_id = config_id
        
        # 替换配置
        index = self.configs.index(old_config)
        self.configs[index] = config
        
        return True
    
    def get_config(self, config_id: str) -> Optional[APIConfig]:
        """获取指定配置"""
        for config in self.configs:
            if config.id == config_id:
                return config
        return None
    
    def get_active_config(self) -> Optional[APIConfig]:
        """获取当前激活的配置"""
        if self.active_config_id:
            return self.get_config(self.active_config_id)
        return None
    
    def set_active_config(self, config_id: str) -> bool:
        """设置激活配置"""
        if self.get_config(config_id):
            self.active_config_id = config_id
            return True
        return False
    
    def get_default_config(self) -> Optional[APIConfig]:
        """获取默认配置"""
        if self.default_config_id:
            return self.get_config(self.default_config_id)
        return None
    
    def get_configs_by_provider(self, provider: str) -> List[APIConfig]:
        """按提供商获取配置列表"""
        return [config for config in self.configs if config.provider == provider]
    
    def clear_default(self):
        """清除所有默认配置"""
        for config in self.configs:
            config.is_default = False
        self.default_config_id = None
    
    def set_default_config(self, config_id: str) -> bool:
        """设置默认配置"""
        config = self.get_config(config_id)
        if not config:
            return False
        
        # 清除其他配置的默认状态
        for c in self.configs:
            c.is_default = False
        
        # 设置新的默认配置
        config.is_default = True
        self.default_config_id = config_id
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """转换为字典格式"""
        return {
            "version": self.version,
            "profiles": {
                "configs": [config.to_dict() for config in self.configs],
                "active_config_id": self.active_config_id,
                "default_config_id": self.default_config_id
            },
            "metadata": {
                "last_modified": datetime.now().isoformat(),
                "config_count": len(self.configs)
            }
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ConfigProfile':
        """从字典创建实例"""
        profile = cls()
        profile.version = data.get("version", "1.0")
        
        profiles_data = data.get("profiles", {})
        configs_data = profiles_data.get("configs", [])
        
        for config_data in configs_data:
            try:
                config = APIConfig.from_dict(config_data)
                profile.configs.append(config)
            except Exception as e:
                print(f"加载配置失败: {e}")
                continue
        
        profile.active_config_id = profiles_data.get("active_config_id")
        profile.default_config_id = profiles_data.get("default_config_id")
        
        return profile