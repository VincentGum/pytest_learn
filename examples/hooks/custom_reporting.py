# 自定义测试报告与结果统计 Hook 示例
import pytest
import time
import json
import os
from datetime import datetime
from typing import Dict, List, Any

# 测试结果收集器
class TestResultCollector:
    def __init__(self):
        self.start_time = None
        self.end_time = None
        self.results = []
        self.stats = {
            "total": 0,
            "passed": 0,
            "failed": 0,
            "skipped": 0,
            "xfailed": 0,
            "xpassed": 0
        }
        self.duration_by_module = {}
        self.duration_by_marker = {}
    
    def record_test_start(self, item):
        """记录测试开始"""
        item._test_start_time = time.time()
        self.stats["total"] += 1
    
    def record_test_result(self, item, outcome):
        """记录测试结果"""
        duration = time.time() - item._test_start_time
        
        # 收集测试标记
        markers = [mark.name for mark in item.iter_markers()]
        
        # 收集模块信息
        module_name = item.module.__name__
        
        # 更新统计信息
        if outcome == "passed":
            self.stats["passed"] += 1
        elif outcome == "failed":
            self.stats["failed"] += 1
        elif outcome == "skipped":
            self.stats["skipped"] += 1
        elif outcome == "xfailed":
            self.stats["xfailed"] += 1
        elif outcome == "xpassed":
            self.stats["xpassed"] += 1
        
        # 更新模块耗时统计
        if module_name not in self.duration_by_module:
            self.duration_by_module[module_name] = {"total": 0, "count": 0}
        self.duration_by_module[module_name]["total"] += duration
        self.duration_by_module[module_name]["count"] += 1
        
        # 更新标记耗时统计
        for marker in markers:
            if marker not in self.duration_by_marker:
                self.duration_by_marker[marker] = {"total": 0, "count": 0}
            self.duration_by_marker[marker]["total"] += duration
            self.duration_by_marker[marker]["count"] += 1
        
        # 记录详细结果
        self.results.append({
            "name": item.nodeid,
            "module": module_name,
            "markers": markers,
            "outcome": outcome,
            "duration": duration,
            "start_time": item._test_start_time
        })
    
    def generate_summary(self) -> Dict[str, Any]:
        """生成测试结果摘要"""
        # 计算平均耗时
        for module in self.duration_by_module:
            stats = self.duration_by_module[module]
            stats["average"] = stats["total"] / stats["count"] if stats["count"] > 0 else 0
        
        for marker in self.duration_by_marker:
            stats = self.duration_by_marker[marker]
            stats["average"] = stats["total"] / stats["count"] if stats["count"] > 0 else 0
        
        # 计算整体耗时
        total_duration = self.end_time - self.start_time if self.end_time and self.start_time else 0
        
        return {
            "stats": self.stats,
            "total_duration": total_duration,
            "avg_duration_per_test": total_duration / self.stats["total"] if self.stats["total"] > 0 else 0,
            "duration_by_module": self.duration_by_module,
            "duration_by_marker": self.duration_by_marker,
            "timestamp": datetime.now().isoformat()
        }
    
    def save_results(self, output_dir="test_reports"):
        """保存测试结果到文件"""
        os.makedirs(output_dir, exist_ok=True)
        
        # 保存详细结果
        with open(os.path.join(output_dir, "detailed_results.json"), "w") as f:
            json.dump(self.results, f, indent=2)
        
        # 保存摘要
        summary = self.generate_summary()
        with open(os.path.join(output_dir, "summary.json"), "w") as f:
            json.dump(summary, f, indent=2)
        
        return summary

# 全局结果收集器实例
_result_collector = TestResultCollector()

def pytest_sessionstart(session):
    """测试会话开始时初始化结果收集器"""
    _result_collector.start_time = time.time()

def pytest_sessionfinish(session, exitstatus):
    """测试会话结束时保存结果"""
    _result_collector.end_time = time.time()
    
    # 保存结果到文件
    summary = _result_collector.save_results()
    
    # 打印摘要到控制台
    print(f"\n===== 自定义测试报告 =====")
    print(f"总测试数: {summary['stats']['total']}")
    print(f"通过: {summary['stats']['passed']} | 失败: {summary['stats']['failed']} | 跳过: {summary['stats']['skipped']}")
    print(f"总耗时: {summary['total_duration']:.2f} 秒")
    print(f"平均每个测试耗时: {summary['avg_duration_per_test']:.2f} 秒")
    print(f"\n模块耗时统计:")
    for module, stats in sorted(summary['duration_by_module'].items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"  {module}: 总耗时 {stats['total']:.2f}秒, 平均 {stats['average']:.2f}秒 ({stats['count']}个测试)")
    print(f"\n标记耗时统计:")
    for marker, stats in sorted(summary['duration_by_marker'].items(), key=lambda x: x[1]['total'], reverse=True):
        print(f"  @pytest.mark.{marker}: 总耗时 {stats['total']:.2f}秒, 平均 {stats['average']:.2f}秒 ({stats['count']}个测试)")

def pytest_runtest_setup(item):
    """记录测试开始"""
    _result_collector.record_test_start(item)

def pytest_runtest_makereport(item, call):
    """生成测试报告并记录结果"""
    report = call.get_result()
    
    if report.when == "call":
        # 确定测试结果
        outcome = "passed"
        if report.skipped:
            outcome = "skipped"
        elif report.failed:
            outcome = "failed"
        elif hasattr(report, "wasxfail"):
            if report.passed:
                outcome = "xpassed"
            else:
                outcome = "xfailed"
        
        # 记录测试结果
        _result_collector.record_test_result(item, outcome)

def pytest_terminal_summary(terminalreporter, exitstatus, config):
    """在终端报告中添加自定义信息"""
    # 获取最慢的5个测试
    slow_tests = sorted(_result_collector.results, key=lambda x: x["duration"], reverse=True)[:5]
    
    if slow_tests:
        terminalreporter.write_sep("-", "最慢的5个测试")
        for test in slow_tests:
            terminalreporter.write_line(f"{test['name']}: {test['duration']:.2f} 秒 ({test['outcome']})")
    
    # 添加自定义报告文件位置
    terminalreporter.write_sep("-", "测试报告文件")
    terminalreporter.write_line("详细结果: test_reports/detailed_results.json")
    terminalreporter.write_line("测试摘要: test_reports/summary.json")
