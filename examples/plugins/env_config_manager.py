# 环境配置管理插件
import os
import json
import yaml
import pytest
from typing import Dict, Any, Optional

# 插件元数据
__version__ = "1.0.0"
__description__ = "环境配置管理插件，支持多环境测试配置"

def pytest_addoption(parser):
    """添加命令行参数选项"""
    group = parser.getgroup("env_config", "环境配置管理")
    group.addoption(
        "--env",
        action="store",
        default="development",
        dest="environment",
        help="指定测试环境: development, testing, staging, production"
    )
    group.addoption(
        "--config-dir",
        action="store",
        default="configs",
        dest="config_dir",
        help="配置文件目录路径"
    )

def pytest_configure(config):
    """配置插件"""
    # 获取环境名称
    environment = config.getoption("environment")
    config_dir = config.getoption("config_dir")
    
    # 创建环境配置管理器实例
    config._env_config_manager = EnvironmentConfigManager(environment, config_dir)
    
    # 添加插件信息到配置对象
    config.metadata["env_plugin"] = {
        "version": __version__,
        "environment": environment,
        "config_dir": config_dir
    }

class EnvironmentConfigManager:
    """环境配置管理器"""
    def __init__(self, environment: str, config_dir: str):
        self.environment = environment
        self.config_dir = config_dir
        self.config_cache: Dict[str, Any] = {}
        self._load_environment_config()
    
    def _load_environment_config(self):
        """加载环境配置"""
        # 加载环境特定配置
        env_config_file = os.path.join(self.config_dir, f"{self.environment}.yaml")
        if os.path.exists(env_config_file):
            try:
                with open(env_config_file, 'r', encoding='utf-8') as f:
                    self.config_cache.update(yaml.safe_load(f) or {})
                    print(f"已加载环境配置: {env_config_file}")
            except Exception as e:
                print(f"加载环境配置失败 {env_config_file}: {e}")
        
        # 加载通用配置
        common_config_file = os.path.join(self.config_dir, "common.yaml")
        if os.path.exists(common_config_file):
            try:
                with open(common_config_file, 'r', encoding='utf-8') as f:
                    common_config = yaml.safe_load(f) or {}
                    # 通用配置不覆盖环境特定配置
                    for key, value in common_config.items():
                        if key not in self.config_cache:
                            self.config_cache[key] = value
                    print(f"已加载通用配置: {common_config_file}")
            except Exception as e:
                print(f"加载通用配置失败 {common_config_file}: {e}")
    
    def get_config(self, key: str, default: Any = None) -> Any:
        """获取配置值"""
        # 支持嵌套配置访问，如 "database.url"
        keys = key.split(".")
        value = self.config_cache
        
        for k in keys:
            if isinstance(value, dict) and k in value:
                value = value[k]
            else:
                return default
        
        return value
    
    def get_section(self, section: str) -> Dict[str, Any]:
        """获取配置节"""
        return self.config_cache.get(section, {})
    
    def get_environment(self) -> str:
        """获取当前环境名称"""
        return self.environment
    
    def is_environment(self, env_name: str) -> bool:
        """检查是否是指定环境"""
        return self.environment == env_name
@pytest.fixture(scope="session")
def env_config(request):
    """提供环境配置的fixture"""
    config_manager = request.config._env_config_manager
    
    # 创建一个简单的配置访问器
    class ConfigAccessor:
        def __init__(self, manager):
            self.manager = manager
        
        def get(self, key, default=None):
            return self.manager.get_config(key, default)
        
        def get_section(self, section):
            return self.manager.get_section(section)
        
        def get_environment(self):
            return self.manager.get_environment()
        
        def is_development(self):
            return self.manager.is_environment("development")
        
        def is_testing(self):
            return self.manager.is_environment("testing")
        
        def is_staging(self):
            return self.manager.is_environment("staging")
        
        def is_production(self):
            return self.manager.is_environment("production")
        
        def __getattr__(self, name):
            """支持通过属性访问配置节"""
            return self.get_section(name)
    
    return ConfigAccessor(config_manager)
@pytest.fixture(scope="session")
def base_url(env_config):
    """提供基础URL的fixture"""
    return env_config.get("base_url", "http://localhost:8000")
@pytest.fixture(scope="session")
def api_credentials(env_config):
    """提供API凭证的fixture"""
    return {
        "username": env_config.get("api.username", "test_user"),
        "password": env_config.get("api.password", "test_password"),
        "api_key": env_config.get("api.key")
    }

# 使用示例：
"""
# 1. 创建配置文件
# configs/development.yaml:
# base_url: http://dev-api.example.com
# database:
#   host: localhost
#   port: 5432
#   name: test_db
#
# 2. 在测试中使用
# def test_api_access(base_url, api_credentials):
#     print(f"访问环境: {base_url}")
#     print(f"使用凭证: {api_credentials['username']}")
#     # 测试代码...
#
# 3. 运行测试
# pytest tests/ --env=development
"""
