# 智能重试与报告增强插件
import pytest
import time
import os
import json
import traceback
from datetime import datetime
from typing import Dict, Any, List, Optional, Set
import logging

# 插件元数据
__version__ = "1.0.0"
__description__ = "智能重试与报告增强插件，支持不稳定测试的自动重试和详细报告生成"

# 配置日志记录器
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("smart_retry_plugin")

def pytest_addoption(parser):
    """添加命令行参数选项"""
    group = parser.getgroup("smart_retry", "智能重试设置")
    group.addoption(
        "--max-retries",
        action="store",
        type=int,
        default=2,
        dest="max_retries",
        help="测试失败后的最大重试次数"
    )
    group.addoption(
        "--retry-delay",
        action="store",
        type=float,
        default=1.0,
        dest="retry_delay",
        help="重试之间的延迟时间（秒）"
    )
    group.addoption(
        "--failures-report",
        action="store",
        default="failure_analysis.json",
        dest="failures_report",
        help="失败分析报告文件路径"
    )
    group.addoption(
        "--retry-all",
        action="store_true",
        default=False,
        dest="retry_all",
        help="对所有测试启用重试（不仅是标记的测试）"
    )

def pytest_configure(config):
    """配置插件"""
    # 添加自定义标记
    config.addinivalue_line(
        "markers", 
        "retry(max_retries=None, delay=None): 标记测试可以重试，并可指定最大重试次数和延迟时间"
    )
    config.addinivalue_line(
        "markers", 
        "flaky(reason=None): 标记测试为不稳定测试，应该重试"
    )
    
    # 创建重试管理器实例
    max_retries = config.getoption("max_retries")
    retry_delay = config.getoption("retry_delay")
    failures_report = config.getoption("failures_report")
    retry_all = config.getoption("retry_all")
    
    config._retry_manager = RetryManager(
        max_retries=max_retries,
        retry_delay=retry_delay,
        failures_report=failures_report,
        retry_all=retry_all
    )
    
    # 添加插件信息到配置对象
    config.metadata["retry_plugin"] = {
        "version": __version__,
        "max_retries": max_retries,
        "retry_delay": retry_delay
    }

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时生成报告"""
    if hasattr(session.config, "_retry_manager"):
        session.config._retry_manager.generate_report()

def pytest_runtest_protocol(item, nextitem):
    """重写测试执行协议以支持重试"""
    # 获取重试管理器
    retry_manager = item.config._retry_manager
    
    # 检查测试是否应该重试
    if not retry_manager.should_retry(item):
        # 不重试，使用默认执行
        return None
    
    # 获取测试的重试配置
    retry_config = retry_manager.get_retry_config(item)
    max_retries = retry_config["max_retries"]
    delay = retry_config["delay"]
    
    # 执行测试并在失败时重试
    for attempt in range(max_retries + 1):
        # 记录尝试信息
        is_last_attempt = (attempt == max_retries)
        logger.info(f"执行测试 {item.nodeid} (尝试 {attempt + 1}/{max_retries + 1})")
        
        # 创建报告对象
        reports = []
        
        # 执行测试的三个阶段
        for when in ("setup", "call", "teardown"):
            # 跳过teardown阶段的重试
            if when == "teardown" and attempt > 0:
                continue
            
            # 执行阶段
            item.ihook.pytest_runtest_logstart(nodeid=item.nodeid, location=item.location)
            rep = call_and_report(item, when)
            reports.append(rep)
            
            # 如果阶段失败且不是最后一次尝试，跳出循环进行重试
            if rep.failed and when == "call" and not is_last_attempt:
                logger.warning(f"测试 {item.nodeid} 失败，将在 {delay}秒后重试...")
                retry_manager.record_failure(item, rep, attempt)
                
                # 等待指定延迟时间
                time.sleep(delay)
                break
            
            # 如果阶段失败且是最后一次尝试，继续执行teardown
            if rep.failed:
                break
        
        # 如果所有阶段都通过，标记为成功并重试
        if all(not rep.failed for rep in reports if rep.when == "call"):
            if attempt > 0:
                logger.info(f"测试 {item.nodeid} 在第 {attempt + 1} 次尝试中通过")
                retry_manager.record_retry_success(item, attempt)
            break
        
        # 如果是最后一次尝试且失败，记录最终失败
        if is_last_attempt:
            logger.error(f"测试 {item.nodeid} 在 {max_retries + 1} 次尝试后最终失败")
            retry_manager.record_final_failure(item, reports)
    
    # 返回True表示我们已经处理了测试执行
    return True

def call_and_report(item, when):
    """执行测试阶段并生成报告"""
    # 这里简化了实现，实际使用时应该使用pytest的内置方法
    try:
        if when == "setup":
            item.session._setupstate.setup(item)
        elif when == "call":
            item.runtest()
        elif when == "teardown":
            item.session._setupstate.teardown_exact(item)
        
        # 创建成功报告
        rep = item.config.hook.pytest_runtest_makereport(item=item, call=None)
        rep.when = when
        rep.failed = False
        rep.passed = True
        return rep
    except Exception as e:
        # 创建失败报告
        rep = item.config.hook.pytest_runtest_makereport(item=item, call=None)
        rep.when = when
        rep.failed = True
        rep.passed = False
        rep.longrepr = f"{str(e)}\n{traceback.format_exc()}"
        return rep

class RetryManager:
    """重试管理器"""
    def __init__(self, max_retries: int = 2, retry_delay: float = 1.0, 
                 failures_report: str = "failure_analysis.json", retry_all: bool = False):
        self.max_retries = max_retries
        self.retry_delay = retry_delay
        self.failures_report = failures_report
        self.retry_all = retry_all
        
        # 统计信息
        self.stats = {
            "total_tests": 0,
            "retried_tests": 0,
            "retry_successes": 0,
            "final_failures": 0,
            "attempts": {}
        }
        
        # 失败记录
        self.failures = []
        self.retry_history = []
        
        # 已处理的测试集（避免重复处理）
        self.processed_tests: Set[str] = set()
    
    def should_retry(self, item) -> bool:
        """检查测试是否应该重试"""
        # 避免重复处理
        if item.nodeid in self.processed_tests:
            return False
        self.processed_tests.add(item.nodeid)
        
        # 增加测试总数
        self.stats["total_tests"] += 1
        
        # 检查是否有retry标记
        retry_marker = item.get_closest_marker("retry")
        if retry_marker:
            return True
        
        # 检查是否有flaky标记
        flaky_marker = item.get_closest_marker("flaky")
        if flaky_marker:
            return True
        
        # 如果设置了retry_all，对所有测试启用重试
        return self.retry_all
    
    def get_retry_config(self, item) -> Dict[str, Any]:
        """获取测试的重试配置"""
        config = {
            "max_retries": self.max_retries,
            "delay": self.retry_delay
        }
        
        # 检查retry标记中的配置
        retry_marker = item.get_closest_marker("retry")
        if retry_marker:
            if "max_retries" in retry_marker.kwargs:
                config["max_retries"] = retry_marker.kwargs["max_retries"]
            if "delay" in retry_marker.kwargs:
                config["delay"] = retry_marker.kwargs["delay"]
        
        return config
    
    def record_failure(self, item, report, attempt: int):
        """记录测试失败"""
        self.retry_history.append({
            "nodeid": item.nodeid,
            "attempt": attempt + 1,
            "status": "failed",
            "timestamp": datetime.now().isoformat(),
            "error": str(report.longrepr) if hasattr(report, "longrepr") else "Unknown error"
        })
    
    def record_retry_success(self, item, attempt: int):
        """记录重试成功"""
        self.stats["retried_tests"] += 1
        self.stats["retry_successes"] += 1
        
        if item.nodeid not in self.stats["attempts"]:
            self.stats["attempts"][item.nodeid] = 0
        self.stats["attempts"][item.nodeid] = attempt + 1
        
        self.retry_history.append({
            "nodeid": item.nodeid,
            "attempt": attempt + 1,
            "status": "success",
            "timestamp": datetime.now().isoformat()
        })
    
    def record_final_failure(self, item, reports):
        """记录最终失败"""
        self.stats["retried_tests"] += 1
        self.stats["final_failures"] += 1
        
        # 获取调用阶段的报告
        call_report = next((rep for rep in reports if rep.when == "call"), None)
        
        self.failures.append({
            "nodeid": item.nodeid,
            "error": str(call_report.longrepr) if call_report and hasattr(call_report, "longrepr") else "Unknown error",
            "timestamp": datetime.now().isoformat(),
            "markers": [mark.name for mark in item.iter_markers()]
        })
    
    def generate_report(self):
        """生成失败分析报告"""
        # 计算统计数据
        retry_rate = (self.stats["retried_tests"] / self.stats["total_tests"] * 100 
                     if self.stats["total_tests"] > 0 else 0)
        success_rate_after_retry = (self.stats["retry_successes"] / self.stats["retried_tests"] * 100 
                                  if self.stats["retried_tests"] > 0 else 0)
        
        # 创建报告数据
        report = {
            "metadata": {
                "timestamp": datetime.now().isoformat(),
                "plugin_version": __version__,
                "max_retries": self.max_retries,
                "retry_delay": self.retry_delay
            },
            "statistics": {
                "total_tests": self.stats["total_tests"],
                "retried_tests": self.stats["retried_tests"],
                "retry_successes": self.stats["retry_successes"],
                "final_failures": self.stats["final_failures"],
                "retry_rate": f"{retry_rate:.2f}%",
                "success_rate_after_retry": f"{success_rate_after_retry:.2f}%",
                "attempts_per_test": self.stats["attempts"]
            },
            "failures": self.failures,
            "retry_history": self.retry_history
        }
        
        # 保存报告到文件
        with open(self.failures_report, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        
        print(f"\n===== 智能重试报告 =====")
        print(f"总测试数: {self.stats['total_tests']}")
        print(f"重试测试数: {self.stats['retried_tests']} ({retry_rate:.2f}%)")
        print(f"重试成功数: {self.stats['retry_successes']} ({success_rate_after_retry:.2f}%)")
        print(f"最终失败数: {self.stats['final_failures']}")
        print(f"失败分析报告已保存到: {self.failures_report}")
        
        # 显示需要关注的不稳定测试
        if self.retry_history:
            unstable_tests = set()
            for record in self.retry_history:
                if record["status"] == "failed":
                    unstable_tests.add(record["nodeid"])
            
            if unstable_tests:
                print(f"\n需要关注的不稳定测试 ({len(unstable_tests)}):")
                for test in list(unstable_tests)[:5]:  # 只显示前5个
                    print(f"  - {test}")
                if len(unstable_tests) > 5:
                    print(f"  ... 还有 {len(unstable_tests) - 5} 个不稳定测试")

# 使用示例：
"""
# 1. 标记不稳定测试
# @pytest.mark.flaky(reason="网络不稳定")
# def test_network_operation():
#     # 可能不稳定的网络测试
#     # ...
#
# 2. 自定义重试参数
# @pytest.mark.retry(max_retries=3, delay=2.0)
# def test_external_service():
#     # 需要更多重试次数的测试
#     # ...
#
# 3. 运行测试
# pytest tests/ --max-retries=2 --retry-delay=1.5 --failures-report=analysis/report.json
"""
