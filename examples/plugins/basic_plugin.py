# 高级插件示例
import pytest

class AdvancedPlugin:
    def __init__(self):
        self.name = "AdvancedPlugin"
        self.version = "1.0.0"

def pytest_configure(config):
    """配置pytest，初始化插件"""
    config._advanced_plugin = AdvancedPlugin()
    config.addinivalue_line("markers", "database: 需要数据库的测试")

# 提供自定义fixture
@pytest.fixture(scope="session")
def api_version(pytestconfig):
    """提供API版本配置"""
    return pytestconfig.getoption("--api-version")
