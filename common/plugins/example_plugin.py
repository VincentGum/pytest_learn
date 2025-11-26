import pytest
import time
import os

# Hook 1: 自定义测试发现后的处理
def pytest_collection_modifyitems(config, items):
    """修改收集到的测试项，根据环境和标记进行过滤"""
    env = config.getoption("--env")
    # 生产环境跳过慢测试
    if env == "prod":
        for item in items:
            if "slow" in [m.name for m in item.iter_markers()]:
                item.add_marker(pytest.mark.skip(reason="生产环境跳过慢测试"))
    
    # 按标记对测试排序
    def item_priority(item):
        markers = [m.name for m in item.iter_markers()]
        if "unit" in markers:
            return 0
        elif "contract" in markers:
            return 1
        elif "integration" in markers:
            return 2
        elif "e2e" in markers:
            return 3
        return 4
    
    items.sort(key=item_priority)

# Hook 2: 测试会话开始时执行
def pytest_sessionstart(session):
    """测试会话开始时记录时间和环境信息"""
    session.start_time = time.time()
    print(f"\n测试会话开始于: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"运行环境: {session.config.getoption('--env')}")
    import sys
    print(f"Python版本: {sys.version}")

# Hook 3: 测试会话结束时执行
def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时计算总耗时"""
    duration = time.time() - session.start_time
    print(f"\n测试会话总耗时: {duration:.2f}秒")

# Hook 4: 自定义终端输出摘要
def pytest_terminal_summary(terminalreporter, exitstatus):
    """自定义测试结束后的输出摘要"""
    terminalreporter.write_sep("=", "自定义摘要: 用例统计")
    counts = terminalreporter.stats
    passed = len(counts.get("passed", []))
    failed = len(counts.get("failed", []))
    skipped = len(counts.get("skipped", []))
    xfailed = len(counts.get("xfailed", []))
    terminalreporter.write_line(f"通过: {passed}  失败: {failed}  跳过: {skipped}  xfail: {xfailed}")
    
    # 输出失败测试的详细信息
    if failed > 0:
        terminalreporter.write_sep("-", "失败测试详情")
        for item in counts.get("failed", []):
            terminalreporter.write_line(f"失败: {item.nodeid} - {str(item.longrepr).split('\n')[-1]}")

# Hook 5: 测试函数执行前执行
def pytest_runtest_setup(item):
    """测试函数执行前的设置"""
    # 可以在这里添加额外的测试前置条件检查
    markers = [m.name for m in item.iter_markers()]
    if "require_db" in markers and not os.environ.get("DB_AVAILABLE"):
        pytest.skip("数据库不可用，跳过测试")

# Hook 6: 注册额外的fixture
def pytest_configure(config):
    """配置pytest，注册额外的标记"""
    # 注册自定义标记
    config.addinivalue_line("markers", "require_db: 需要数据库连接的测试")
    config.addinivalue_line("markers", "require_api: 需要API访问的测试")
    config.addinivalue_line("markers", "performance: 性能测试")
