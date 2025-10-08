"""
配置管理器
负责配置的加载、保存、导入、导出等功能
"""

import json
import os
from pathlib import Path
from typing import List, Optional
import shutil
from datetime import datetime
import dotenv
import uuid

from .config_models import APIConfig, ConfigProfile, ValidationResult, TestResult

class ConfigManager:
    """配置管理核心类"""
    
    def __init__(self, config_dir: Optional[str] = None):
        """初始化配置管理器"""
        if config_dir is None:
            config_dir = os.path.join(os.path.expanduser("~"), ".pdfoptimizer")
        
        self.config_dir = Path(config_dir)
        self.config_file = self.config_dir / "ocr_configs.json"
        self.backup_dir = self.config_dir / "backups"
        self.env_file = self.config_dir / ".env"
        
        # 确保目录存在
        self.config_dir.mkdir(exist_ok=True)
        self.backup_dir.mkdir(exist_ok=True)
    
    def load_configs(self) -> ConfigProfile:
        """加载配置文件"""
        if not self.config_file.exists():
            # 尝试从旧的.env文件迁移配置
            return self._migrate_from_old_config()
        
        try:
            with open(self.config_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return ConfigProfile.from_dict(data)
        except Exception as e:
            print(f"加载配置文件失败: {e}")
            # 尝试从备份恢复
            return self._restore_from_backup()
    
    def save_configs(self, profile: ConfigProfile, create_backup: bool = True) -> bool:
        """保存配置文件"""
        try:
            # 创建备份
            if create_backup and self.config_file.exists():
                self._create_backup()
            
            # 保存配置
            data = profile.to_dict()
            with open(self.config_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"保存配置文件失败: {e}")
            return False
    
    def export_configs(self, file_path: str, config_ids: Optional[List[str]] = None) -> bool:
        """导出配置到指定文件"""
        try:
            profile = self.load_configs()
            
            # 如果指定了配置ID，只导出这些配置
            if config_ids:
                exported_configs = []
                for config_id in config_ids:
                    config = profile.get_config(config_id)
                    if config:
                        exported_configs.append(config)
                
                # 创建新的配置文件只包含选中的配置
                exported_profile = ConfigProfile()
                exported_profile.configs = exported_configs
                
                data = exported_profile.to_dict()
            else:
                data = profile.to_dict()
            
            with open(file_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
            
            return True
        except Exception as e:
            print(f"导出配置失败: {e}")
            return False
    
    def import_configs(self, file_path: str, merge: bool = True) -> List[APIConfig]:
        """从指定文件导入配置"""
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            imported_profile = ConfigProfile.from_dict(data)
            current_profile = self.load_configs()
            
            imported_configs = []
            
            if merge:
                # 合并模式：添加不重复的配置
                for config in imported_profile.configs:
                    # 检查名称是否重复
                    if not any(c.name == config.name for c in current_profile.configs):
                        # 生成新的ID以避免冲突
                        config.id = str(uuid.uuid4())
                        current_profile.add_config(config)
                        imported_configs.append(config)
            else:
                # 替换模式：完全替换当前配置
                current_profile = imported_profile
                imported_configs = imported_profile.configs
            
            # 保存更新后的配置
            self.save_configs(current_profile)
            
            return imported_configs
        except Exception as e:
            print(f"导入配置失败: {e}")
            return []
    
    def validate_config(self, config: APIConfig) -> ValidationResult:
        """验证配置"""
        return config.validate()
    
    def test_connection(self, config: APIConfig) -> TestResult:
        """测试API连接"""
        import time
        import httpx
        
        start_time = time.time()
        
        try:
            if config.provider == "Mistral API":
                # 测试Mistral API
                from mistralai import Mistral
                client = Mistral(api_key=config.api_key)
                
                # 尝试获取模型列表作为连接测试
                models = client.models.list()
                response_time = time.time() - start_time
                
                return TestResult(
                    success=True,
                    message="连接成功",
                    response_time=response_time,
                    details={"model_count": len(models.data)}
                )
            
            elif config.provider == "OpenAI-Compatible":
                # 测试OpenAI兼容API
                headers = {
                    "Authorization": f"Bearer {config.api_key}",
                    "Content-Type": "application/json"
                }
                
                with httpx.Client(timeout=10.0) as client:
                    response = client.get(
                        f"{config.api_base_url.rstrip('/')}/models",
                        headers=headers
                    )
                    response.raise_for_status()
                    
                    response_time = time.time() - start_time
                    data = response.json()
                    models = data.get("data", [])
                    
                    return TestResult(
                        success=True,
                        message="连接成功",
                        response_time=response_time,
                        details={"model_count": len(models)}
                    )
            
            else:
                return TestResult(
                    success=False,
                    message=f"不支持的提供商: {config.provider}"
                )
        
        except Exception as e:
            response_time = time.time() - start_time
            return TestResult(
                success=False,
                message=f"连接失败: {str(e)}",
                response_time=response_time
            )
    
    def _create_backup(self):
        """创建配置文件备份"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_file = self.backup_dir / f"ocr_configs_backup_{timestamp}.json"
        
        try:
            shutil.copy2(self.config_file, backup_file)
            
            # 清理旧备份（保留最近10个）
            backups = sorted(self.backup_dir.glob("ocr_configs_backup_*.json"))
            if len(backups) > 10:
                for old_backup in backups[:-10]:
                    old_backup.unlink()
        except Exception as e:
            print(f"创建备份失败: {e}")
    
    def _restore_from_backup(self) -> ConfigProfile:
        """从备份恢复配置"""
        try:
            backups = sorted(self.backup_dir.glob("ocr_configs_backup_*.json"))
            if backups:
                # 使用最新的备份
                latest_backup = backups[-1]
                with open(latest_backup, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                print(f"从备份恢复配置: {latest_backup.name}")
                return ConfigProfile.from_dict(data)
        except Exception as e:
            print(f"从备份恢复配置失败: {e}")
        
        return ConfigProfile()
    
    def _migrate_from_old_config(self) -> ConfigProfile:
        """从旧的.env文件迁移配置"""
        if not self.env_file.exists():
            return ConfigProfile()
        
        try:
            # 加载旧配置
            dotenv.load_dotenv(dotenv_path=self.env_file, override=True)
            
            profile = ConfigProfile()
            
            # 获取旧配置值
            provider = os.getenv("OCR_API_PROVIDER", "OpenAI-Compatible")
            api_key = os.getenv("MISTRAL_API_KEY" if provider == "Mistral API" else "OPENAI_API_KEY", "")
            api_base_url = os.getenv("OCR_API_BASE_URL", "https://api.openai.com/v1")
            model_name = os.getenv("MISTRAL_MODEL_NAME" if provider == "Mistral API" else "OPENAI_MODEL_NAME", 
                                 "mistral-ocr-latest" if provider == "Mistral API" else "gpt-4o")
            temperature = float(os.getenv("OCR_TEMPERATURE", "1.0"))
            prompt = os.getenv("OCR_PROMPT", "这是一个PDF页面。请准确识别所有内容，并将其转换为结构良好的Markdown格式。")
            save_mode = os.getenv("OCR_SAVE_MODE", "per_page")
            
            if api_key:
                # 创建迁移的配置
                config = APIConfig(
                    name=f"迁移的{provider}配置",
                    provider=provider,
                    api_key=api_key,
                    api_base_url=api_base_url,
                    model_name=model_name,
                    temperature=temperature,
                    prompt=prompt,
                    save_mode=save_mode,
                    is_default=True
                )
                
                profile.add_config(config)
                
                # 保存新配置
                self.save_configs(profile)
                
                # 重命名旧配置文件
                migrated_env = self.config_dir / ".env.migrated"
                if not migrated_env.exists():
                    self.env_file.rename(migrated_env)
                
                print(f"成功迁移旧配置到新系统: {config.name}")
            
            return profile
        except Exception as e:
            print(f"迁移旧配置失败: {e}")
            return ConfigProfile()