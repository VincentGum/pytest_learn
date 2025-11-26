import pytest
import json
import os
from datetime import datetime

# 注册插件信息
class AdvancedPlugin:
    def __init__(self):
        self.name = "AdvancedPlugin"
        self.version = "1.0.0"

# 插件入口函数
def pytest_configure(config):
    """配置pytest，初始化插件"""
    # 注册插件对象
    config._advanced_plugin = AdvancedPlugin()
    # 添加自定义标记
    config.addinivalue_line("markers", "database: 需要数据库的测试")
    config.addinivalue_line("markers", "mock_api: 使用模拟API的测试")
    config.addinivalue_line("markers", "feature_flag: 特性标志测试")
    print(f"\n已加载高级插件: {config._advanced_plugin.name} v{config._advanced_plugin.version}")

# 自定义命令行参数
def pytest_addoption(parser):
    """添加自定义命令行参数"""
    group = parser.getgroup("advanced_plugin", "高级插件选项")
    group.addoption(
        "--api-version",
        action="store",
        default="v1",
        help="指定API版本"
    )
    group.addoption(
        "--export-results",
        action="store_true",
        default=False,
        help="导出测试结果到JSON文件"
    )
    group.addoption(
        "--feature-flags",
        action="store",
        default="{}",
        help="JSON格式的特性标志配置"
    )

# 提供自定义fixture
def pytest_addhooks(pluginmanager):
    """注册自定义钩子"""
    # 这里可以添加自定义钩子定义
    pass

# 全局fixture定义
@pytest.fixture(scope="session")
def api_version(pytestconfig):
    """提供API版本配置的fixture"""
    return pytestconfig.getoption("--api-version")

@pytest.fixture(scope="session")
def feature_flags(pytestconfig):
    """提供特性标志配置的fixture"""
    flags_str = pytestconfig.getoption("--feature-flags")
    try:
        return json.loads(flags_str)
    except json.JSONDecodeError:
        print("警告: 特性标志配置格式错误，使用默认值")
        return {}

@pytest.fixture(scope="function")
def api_client(api_version, feature_flags):
    """提供API客户端的fixture"""
    # 模拟API客户端
    class MockAPIClient:
        def __init__(self, version, flags):
            self.version = version
            self.flags = flags
            self.calls = []
        
        def get(self, endpoint):
            self.calls.append(('GET', endpoint))
            return {"status": "success", "version": self.version}
        
        def post(self, endpoint, data=None):
            self.calls.append(('POST', endpoint, data))
            return {"status": "created", "version": self.version}
    
    client = MockAPIClient(api_version, feature_flags)
    yield client
    # 清理资源
    client.calls.clear()

# 测试运行钩子
def pytest_runtest_protocol(item, nextitem):
    """自定义测试运行协议"""
    # 可以在这里添加测试执行前后的自定义逻辑
    pass

# 结果收集钩子
@pytest.hookimpl(hookwrapper=True)
def pytest_runtest_makereport(item, call):
    """增强测试报告信息"""
    outcome = yield
    report = outcome.get_result()
    
    # 添加自定义属性到报告
    if report.when == "call":
        # 收集测试标记信息
        report.markers_info = [m.name for m in item.iter_markers()]
        # 记录执行时间戳
        report.timestamp = datetime.now().isoformat()

# 会话结束钩子
def pytest_sessionfinish(session, exitstatus):
    """会话结束时导出结果"""
    if session.config.getoption("--export-results"):
        # 收集测试结果
        results = []
        for item in session.items:
            if hasattr(item, "rep_call"):
                report = item.rep_call
                results.append({
                    "nodeid": item.nodeid,
                    "status": report.outcome,
                    "duration": report.duration,
                    "markers": getattr(report, "markers_info", []),
                    "timestamp": getattr(report, "timestamp", None)
                })
        
        # 导出到JSON文件
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"test_results_{timestamp}.json"
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(results, f, indent=2, ensure_ascii=False)
        
        print(f"\n测试结果已导出到: {filename}")

# 测试失败钩子
def pytest_exception_interact(node, call, report):
    """测试异常时的交互处理"""
    if report.failed:
        print(f"\n测试失败详情:")
        print(f"测试: {node.nodeid}")
        print(f"异常类型: {type(call.excinfo.value).__name__}")
        print(f"异常信息: {str(call.excinfo.value)}")
        # 可以在这里添加更多异常处理逻辑，如截图、日志收集等
