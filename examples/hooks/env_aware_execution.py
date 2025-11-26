# 环境感知的测试执行控制 Hook 示例
import pytest
import os
from typing import List

# 环境配置映射
ENV_CONFIG = {
    "dev": {"db_url": "sqlite:///:memory:", "api_url": "http://localhost:8000"},
    "staging": {"db_url": "postgresql://staging:5432/test", "api_url": "https://staging-api.example.com"},
    "prod": {"db_url": "postgresql://prod:5432/test", "api_url": "https://api.example.com"}
}

def pytest_addoption(parser):
    """添加环境选择命令行参数"""
    parser.addoption("--env", action="store", default="dev",
                     help="指定测试环境: dev, staging, prod")

def pytest_configure(config):
    """配置pytest，设置当前环境"""
    # 设置当前环境
    config._current_env = config.getoption("--env")
    print(f"当前测试环境: {config._current_env}")
    
    # 设置环境变量
    os.environ["TEST_ENV"] = config._current_env
    
    # 根据环境设置数据库URL
    if config._current_env in ENV_CONFIG:
        os.environ["DATABASE_URL"] = ENV_CONFIG[config._current_env]["db_url"]

def pytest_collection_modifyitems(config, items: List[pytest.Item]):
    """根据环境过滤测试项"""
    current_env = config.getoption("--env")
    
    # 分离不同环境的测试
    regular_items = []
    skip_items = []
    
    for item in items:
        # 检查测试是否有环境标记
        env_marker = item.get_closest_marker("env")
        if env_marker and env_marker.args:
            # 只在指定环境运行的测试
            allowed_envs = env_marker.args
            if current_env not in allowed_envs:
                skip_items.append((item, f"环境 {current_env} 不在允许的环境列表中: {allowed_envs}"))
                continue
        
        regular_items.append(item)
    
    # 更新测试列表
    items[:] = regular_items
    
    # 跳过不需要运行的测试
    for item, reason in skip_items:
        item.add_marker(pytest.mark.skip(reason=reason))
    
    print(f"环境 {current_env} 过滤结果: 执行 {len(regular_items)} 个测试, 跳过 {len(skip_items)} 个测试")

@pytest.fixture(scope="session")
def test_env(pytestconfig):
    """提供当前测试环境的fixture"""
    return pytestconfig.getoption("--env")

@pytest.fixture(scope="session")
def env_config(test_env):
    """提供当前环境配置的fixture"""
    return ENV_CONFIG.get(test_env, ENV_CONFIG["dev"])
